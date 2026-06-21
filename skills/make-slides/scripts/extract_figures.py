#!/usr/bin/env python3
"""Inventory the figures of a LaTeX paper for slide reuse.

Scans a paper's LaTeX source (a main .tex file; \\input/\\include files are
followed) and reports every figure environment: graphics files, labels,
caption snippets, and how often each figure is referenced in the text
(\\ref/\\autoref/\\cref/\\Cref/\\figref) — the reference count is a strong
signal for which figures carry the talk. Resolves graphics paths the way
LaTeX does (\\graphicspath, extension-less names tried as .pdf/.png/.jpg/
.jpeg/.eps) and can copy the resolved files into a slide-assets directory.

Stdlib only. No network.

Usage:
    python3 extract_figures.py paper/main.tex
    python3 extract_figures.py paper/main.tex --copy-to talk/assets
    python3 extract_figures.py paper/main.tex --json

Exit codes:
    0  inventory produced (even if 0 figures — a clear note is printed)
    1  --copy-to was requested and at least one graphics file could not be
       resolved/copied (inventory still printed)
    2  bad arguments or unreadable input
"""

import argparse
import json
import os
import re
import shutil
import sys

ENV_RE = re.compile(
    r"\\begin\{(figure\*?|teaserfigure|wrapfigure|sidewaysfigure)\}(?:\[[^\]]*\])?"
    r"(.*?)\\end\{\1\}",
    re.S,
)
GRAPHICS_RE = re.compile(r"\\includegraphics\s*(?:\[[^\]]*\])?\s*\{([^}]+)\}")
LABEL_RE = re.compile(r"\\label\{([^}]+)\}")
INPUT_RE = re.compile(r"\\(?:input|include)\{([^}]+)\}")
GRAPHICSPATH_RE = re.compile(r"\\graphicspath\{((?:\s*\{[^}]*\}\s*)+)\}")
REF_RE = re.compile(r"\\(?:ref|autoref|cref|Cref|figref|vref)\*?\{([^}]+)\}")
TABLE_RE = re.compile(r"\\begin\{table\*?\}")
EXTS = ("", ".pdf", ".png", ".jpg", ".jpeg", ".eps")


def fail(msg):
    sys.stderr.write("error: %s\n" % msg)
    return 2


def strip_comments(text):
    """Drop unescaped % comments, line by line."""
    out = []
    for line in text.splitlines():
        i = 0
        while True:
            j = line.find("%", i)
            if j < 0:
                out.append(line)
                break
            if j > 0 and line[j - 1] == "\\":
                i = j + 1
                continue
            out.append(line[:j])
            break
    return "\n".join(out)


def gather_source(main_path, max_depth=8):
    """Read main file + \\input/\\include children (relative to main dir)."""
    base = os.path.dirname(os.path.abspath(main_path))
    seen, chunks = set(), []

    def read(path, depth):
        rp = os.path.abspath(path)
        if rp in seen or depth > max_depth:
            return
        seen.add(rp)
        try:
            with open(rp, "r", encoding="utf-8", errors="replace") as fh:
                text = strip_comments(fh.read())
        except OSError:
            return  # missing child file: skip silently, main is checked upstream
        chunks.append(text)
        for child in INPUT_RE.findall(text):
            child = child.strip()
            if not child.endswith(".tex"):
                child += ".tex"
            read(os.path.join(base, child), depth + 1)

    read(main_path, 0)
    return "\n".join(chunks)


def balanced_arg(text, open_idx):
    """Return content of the brace group starting at text[open_idx] == '{'."""
    depth = 0
    for i in range(open_idx, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[open_idx + 1:i]
    return text[open_idx + 1:]


def extract_caption(body):
    m = re.search(r"\\caption\s*(?:\[[^\]]*\])?\s*\{", body)
    if not m:
        return ""
    cap = balanced_arg(body, m.end() - 1)
    cap = re.sub(r"\\label\{[^}]*\}", "", cap)
    cap = re.sub(r"\\[a-zA-Z]+\*?", " ", cap)
    cap = re.sub(r"[{}~]", " ", cap)
    return re.sub(r"\s+", " ", cap).strip()


def graphics_dirs(text, texdir):
    dirs = [texdir]
    for grp in GRAPHICSPATH_RE.findall(text):
        for d in re.findall(r"\{([^}]*)\}", grp):
            dirs.append(os.path.join(texdir, d))
    return dirs


def resolve(name, dirs):
    name = name.strip()
    for d in dirs:
        for ext in EXTS:
            cand = os.path.join(d, name + ext)
            if os.path.isfile(cand):
                return os.path.normpath(cand)
    return None


def build_inventory(main_path):
    text = gather_source(main_path)
    texdir = os.path.dirname(os.path.abspath(main_path))
    dirs = graphics_dirs(text, texdir)
    ref_counts = {}
    for grp in REF_RE.findall(text):
        for label in grp.split(","):
            label = label.strip()
            ref_counts[label] = ref_counts.get(label, 0) + 1

    figures = []
    for m in ENV_RE.finditer(text):
        body = m.group(2)
        labels = LABEL_RE.findall(body)
        graphics = []
        for g in GRAPHICS_RE.findall(body):
            graphics.append({"name": g.strip(), "resolved": resolve(g, dirs)})
        figures.append({
            "index": len(figures) + 1,
            "env": m.group(1),
            "labels": labels,
            "refs": sum(ref_counts.get(l, 0) for l in labels),
            "graphics": graphics,
            "caption": extract_caption(body),
        })
    n_tables = len(TABLE_RE.findall(text))
    return figures, n_tables


def copy_assets(figures, dest):
    os.makedirs(dest, exist_ok=True)
    copied, missing, used = [], [], {}
    for fig in figures:
        for g in fig["graphics"]:
            if not g["resolved"]:
                missing.append(g["name"])
                continue
            base = os.path.basename(g["resolved"])
            if base in used and used[base] != g["resolved"]:
                base = "fig%d-%s" % (fig["index"], base)
            used.setdefault(base, g["resolved"])
            target = os.path.join(dest, base)
            shutil.copy2(g["resolved"], target)
            g["copied_to"] = target
            copied.append(target)
    return copied, missing


def print_markdown(figures, n_tables, main_path):
    print("# Figure inventory — %s" % main_path)
    print()
    if not figures:
        print("No figure environments found. If the paper keeps figures in a")
        print("separate file, pass the file that contains them.")
        return
    print("| # | label(s) | refs | graphics file | resolved | caption (trimmed) |")
    print("|---|----------|------|---------------|----------|-------------------|")
    for fig in sorted(figures, key=lambda f: -f["refs"]):
        labels = ", ".join(fig["labels"]) or "(none)"
        gfx = "; ".join(g["name"] for g in fig["graphics"]) or "(none — TikZ/pgf?)"
        ok = "yes" if fig["graphics"] and all(g["resolved"] for g in fig["graphics"]) \
            else ("NO" if fig["graphics"] else "n/a")
        cap = fig["caption"][:90] + ("…" if len(fig["caption"]) > 90 else "")
        print("| %d | %s | %d | %s | %s | %s |"
              % (fig["index"], labels, fig["refs"], gfx, ok, cap or "(no caption)"))
    print()
    print("- %d figure environment(s); %d table environment(s) — tables almost"
          % (len(figures), n_tables))
    print("  always need redesign as charts for slides, not direct reuse.")
    print("- Sorted by in-text reference count: the most-referenced figures are")
    print("  usually the ones the talk should be built around.")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Inventory a LaTeX paper's figures (labels, captions, "
        "graphics files, in-text reference counts) for slide reuse; "
        "optionally copy the graphics into a slide-assets directory.")
    parser.add_argument("main_tex", help="path to the paper's main .tex file")
    parser.add_argument("--copy-to", metavar="DIR", default=None,
                        help="copy every resolved graphics file into DIR")
    parser.add_argument("--json", action="store_true",
                        help="emit the inventory as JSON instead of markdown")
    args = parser.parse_args(argv)

    if not os.path.isfile(args.main_tex):
        return fail("cannot read %s — pass the paper's main .tex file" % args.main_tex)
    if not args.main_tex.endswith(".tex"):
        return fail("%s does not look like a .tex file" % args.main_tex)

    figures, n_tables = build_inventory(args.main_tex)

    missing = []
    if args.copy_to is not None:
        try:
            copied, missing = copy_assets(figures, args.copy_to)
        except OSError as exc:
            return fail("could not copy assets: %s" % exc)

    if args.json:
        json.dump({"figures": figures, "tables": n_tables,
                   "missing": missing}, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        print_markdown(figures, n_tables, args.main_tex)
        if args.copy_to is not None:
            print("- Copied resolved graphics to %s/" % args.copy_to.rstrip("/"))

    if missing:
        sys.stderr.write(
            "error: %d graphics file(s) could not be resolved: %s\n"
            "(checked %s relative to the .tex dir and \\graphicspath)\n"
            % (len(missing), ", ".join(missing), "/".join(e or "<as-is>" for e in EXTS)))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
