#!/usr/bin/env python3
"""Minimal YAML-subset loader for research-paper-skills venue profiles.

Stdlib only — NOT a general YAML parser. Supports exactly the subset used
by venues/schema.yml, venues/conferences/*.yml and venues/families/*.yml:

  - nested mappings (2-space indentation)
  - lists of scalars and lists of mappings ("- key: value")
  - flow lists: [references, appendix]
  - folded (>) and literal (|) block scalars
  - single/double-quoted strings (with \\ and \" escapes)
  - comments (full-line and inline), null/~, booleans, ints, floats

Also resolves `family:` inheritance: fields that are null/missing in a
conference profile are filled from venues/families/<family>.yml.

CLI usage (prints the parsed profile as JSON):
    python3 venueyaml.py <profile.yml> [--no-family] [--family-dir DIR]

Exit codes: 0 ok, 2 bad arguments / unreadable file / parse error.
"""

import argparse
import json
import os
import re
import sys

__all__ = ["load", "load_with_family", "VenueYamlError"]


class VenueYamlError(Exception):
    """Raised when the profile cannot be parsed by this YAML subset."""


# --------------------------------------------------------------------------
# scalar handling
# --------------------------------------------------------------------------

_INT_RE = re.compile(r"^-?\d+$")
_FLOAT_RE = re.compile(r"^-?\d+\.\d+$")
_KEY_RE = re.compile(r"^([A-Za-z0-9_.-]+):(\s+|$)")


def _strip_inline_comment(text):
    """Remove an inline comment, respecting single/double quotes."""
    quote = None
    i = 0
    while i < len(text):
        ch = text[i]
        if quote:
            if ch == "\\" and quote == '"':
                i += 2
                continue
            if ch == quote:
                quote = None
        elif ch in ("'", '"'):
            quote = ch
        elif ch == "#" and (i == 0 or text[i - 1] in " \t"):
            return text[:i].rstrip()
        i += 1
    return text.rstrip()


def _parse_scalar(tok):
    tok = tok.strip()
    if tok == "" or tok in ("null", "Null", "NULL", "~"):
        return None
    if tok in ("true", "True"):
        return True
    if tok in ("false", "False"):
        return False
    if tok.startswith('"') and tok.endswith('"') and len(tok) >= 2:
        body = tok[1:-1]
        return body.replace('\\"', '"').replace("\\\\", "\\")
    if tok.startswith("'") and tok.endswith("'") and len(tok) >= 2:
        return tok[1:-1].replace("''", "'")
    if tok.startswith("[") and tok.endswith("]"):
        inner = tok[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(p) for p in _split_flow(inner)]
    if _INT_RE.match(tok):
        return int(tok)
    if _FLOAT_RE.match(tok):
        return float(tok)
    return tok


def _split_flow(inner):
    """Split 'a, b, "c, d"' on top-level commas."""
    parts, buf, quote = [], "", None
    for ch in inner:
        if quote:
            buf += ch
            if ch == quote:
                quote = None
        elif ch in ("'", '"'):
            quote = ch
            buf += ch
        elif ch == ",":
            parts.append(buf.strip())
            buf = ""
        else:
            buf += ch
    if buf.strip():
        parts.append(buf.strip())
    return parts


# --------------------------------------------------------------------------
# block parsing
# --------------------------------------------------------------------------


class _Lines:
    """Cleaned, indexed view of the file: list of (indent, text)."""

    def __init__(self, raw):
        self.items = []
        for lineno, line in enumerate(raw.splitlines(), 1):
            if "\t" in line[: len(line) - len(line.lstrip())]:
                raise VenueYamlError("line %d: tabs in indentation are not supported" % lineno)
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                # blank/comment lines are kept only as markers inside block scalars,
                # which are collected from the RAW text separately; drop here.
                self.items.append((None, None, lineno))
                continue
            indent = len(line) - len(line.lstrip(" "))
            self.items.append((indent, line.rstrip("\n"), lineno))
        self.n = len(self.items)

    def next_content(self, i):
        while i < self.n and self.items[i][0] is None:
            i += 1
        return i


def _parse_block_scalar(lines, i, key_indent, fold):
    """Collect a > or | block: all following lines indented deeper than key."""
    chunks = []
    while i < lines.n:
        indent, text, _ = lines.items[i]
        if indent is None:  # blank or comment line inside block: paragraph break
            chunks.append("")
            i += 1
            continue
        if indent <= key_indent:
            break
        chunks.append(text.strip())
        i += 1
    # trim trailing blanks
    while chunks and chunks[-1] == "":
        chunks.pop()
    joiner = " " if fold else "\n"
    out = joiner.join(c for c in chunks if c != "") if fold else joiner.join(chunks)
    return out.strip(), i


def _parse_node(lines, i, indent):
    """Parse mapping or list starting at index i with the given indent."""
    i = lines.next_content(i)
    if i >= lines.n:
        return None, i
    _, text, _ = lines.items[i]
    if text.lstrip().startswith("- "):
        return _parse_list(lines, i, indent)
    return _parse_mapping(lines, i, indent)


def _parse_mapping(lines, i, indent):
    out = {}
    while True:
        i = lines.next_content(i)
        if i >= lines.n:
            break
        cur_indent, text, lineno = lines.items[i]
        if cur_indent < indent:
            break
        if cur_indent > indent:
            raise VenueYamlError("line %d: unexpected indentation" % lineno)
        content = _strip_inline_comment(text.strip())
        if content.startswith("- "):
            break
        m = _KEY_RE.match(content)
        if not m:
            raise VenueYamlError("line %d: expected 'key: value', got %r" % (lineno, content))
        key = m.group(1)
        rest = content[m.end():].strip()
        if rest in (">", ">-", "|", "|-"):
            value, i = _parse_block_scalar(lines, i + 1, cur_indent, fold=rest.startswith(">"))
        elif rest == "":
            j = lines.next_content(i + 1)
            if j < lines.n and lines.items[j][0] is not None and lines.items[j][0] > cur_indent:
                value, i = _parse_node(lines, j, lines.items[j][0])
            else:
                value, i = None, i + 1
        else:
            value, i = _parse_scalar(rest), i + 1
        out[key] = value
    return out, i


def _parse_list(lines, i, indent):
    out = []
    while True:
        i = lines.next_content(i)
        if i >= lines.n:
            break
        cur_indent, text, lineno = lines.items[i]
        if cur_indent is None or cur_indent != indent:
            break
        content = _strip_inline_comment(text.strip())
        if not content.startswith("- "):
            break
        rest = content[2:].strip()
        item_indent = cur_indent + 2
        if _KEY_RE.match(rest):
            # inline mapping start: pretend this line is "key: value" at item_indent
            lines.items[i] = (item_indent, " " * item_indent + rest, lineno)
            value, i = _parse_mapping(lines, i, item_indent)
        elif rest == "":
            value, i = _parse_node(lines, i + 1, item_indent)
        else:
            value, i = _parse_scalar(rest), i + 1
        out.append(value)
    return out, i


# --------------------------------------------------------------------------
# public API
# --------------------------------------------------------------------------


def load(path):
    """Parse one profile file → dict. Raises VenueYamlError on failure."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            raw = fh.read()
    except OSError as exc:
        raise VenueYamlError("cannot read %s: %s" % (path, exc))
    lines = _Lines(raw)
    i = lines.next_content(0)
    if i >= lines.n:
        raise VenueYamlError("%s: file has no content" % path)
    value, _ = _parse_node(lines, i, lines.items[i][0])
    if not isinstance(value, dict):
        raise VenueYamlError("%s: top level must be a mapping" % path)
    return value


def _deep_fill(target, source):
    """Fill None/missing values in target from source (conference wins)."""
    for key, src_val in source.items():
        if key not in target or target[key] is None:
            target[key] = src_val
        elif isinstance(target[key], dict) and isinstance(src_val, dict):
            _deep_fill(target[key], src_val)
    return target


def load_with_family(path, family_dir=None):
    """Parse a conference profile and fill nulls from its family profile."""
    profile = load(path)
    family = profile.get("family")
    if not family:
        return profile
    if family_dir is None:
        family_dir = os.path.normpath(
            os.path.join(os.path.dirname(os.path.abspath(path)), "..", "families")
        )
    family_path = os.path.join(family_dir, "%s.yml" % family)
    if not os.path.isfile(family_path):
        sys.stderr.write(
            "warning: family profile not found (%s); using conference profile alone\n"
            % family_path
        )
        return profile
    return _deep_fill(profile, load(family_path))


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Parse a venues/*.yml profile (YAML subset, stdlib only) and "
        "print it as JSON. Resolves family: inheritance by default."
    )
    parser.add_argument("profile", help="path to a venue profile .yml")
    parser.add_argument("--no-family", action="store_true",
                        help="do not merge the family profile")
    parser.add_argument("--family-dir", default=None,
                        help="directory containing family profiles "
                        "(default: <profile dir>/../families)")
    args = parser.parse_args(argv)

    try:
        if args.no_family:
            data = load(args.profile)
        else:
            data = load_with_family(args.profile, args.family_dir)
    except VenueYamlError as exc:
        sys.stderr.write("error: %s\n" % exc)
        return 2
    json.dump(data, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
