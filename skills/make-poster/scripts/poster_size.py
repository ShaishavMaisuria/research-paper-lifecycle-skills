#!/usr/bin/env python3
"""Resolve a poster's exact physical dimensions and LaTeX invocation.

Given the board size the venue published (presenter instructions or
acceptance email — poster sizes are NOT in venue profiles and must never
be guessed), prints the exact dimensions in cm/inches, the matching
beamerposter and tikzposter invocations, a font-size table scaled to the
board, the word budget, and minimum raster resolutions for figures.

Accepted --size tokens:
    a0 | a1 | a2          ISO sizes (orientation via --orientation, required)
    <W>x<H>in | <W>x<H>cm custom printed size, width x height as printed
                          (e.g. 36x48in, 91.44x121.92cm, 72x36in)

Passing --venue-profile only adds venue context and the live URL to
re-verify against; the size always comes from you.

Stdlib only. No network.

Usage:
    python3 poster_size.py --size a0 --orientation portrait
    python3 poster_size.py --size 36x48in
    python3 poster_size.py --size 36x48in --board 48x96in
    python3 poster_size.py --size a0 --orientation portrait \\
        --venue-profile venues/conferences/sigspatial-2026.yml --json

Exit codes: 0 ok; 1 poster does not fit the --board limit; 2 bad
arguments or unreadable profile.
"""

import argparse
import json
import re
import sys

CM_PER_IN = 2.54
ISO_SIZES_CM = {  # portrait (width, height) in cm
    "a0": (84.1, 118.9),
    "a1": (59.4, 84.1),
    "a2": (42.0, 59.4),
}
CUSTOM_RE = re.compile(r"^(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)(in|cm)$")
PROFILE_FIELD_RE = re.compile(r"^(id|name|year|cfp_url|website):\s*(.+?)\s*$")

# baseline type scale at A0 (pt); scaled linearly by the short side
TYPE_SCALE_A0 = [
    ("Title (claim-style headline)", 96),
    ("Authors & affiliations", 54),
    ("Section / block headers", 60),
    ("Body text (floor: 24pt)", 30),
    ("Captions & axis labels", 24),
    ("References / fine print", 20),
]
WORDS_TARGET, WORDS_MAX = 450, 800


def fail(msg):
    sys.stderr.write("error: %s\n" % msg)
    return 2


def parse_size_token(token):
    """Return (w_cm, h_cm, iso_name_or_None) as printed; ISO returns portrait dims."""
    token = token.strip().lower()
    if token in ISO_SIZES_CM:
        w, h = ISO_SIZES_CM[token]
        return w, h, token
    m = CUSTOM_RE.match(token)
    if not m:
        raise ValueError(
            "unrecognized size %r — use a0/a1/a2 or <W>x<H>in / <W>x<H>cm "
            "(e.g. 36x48in)" % token)
    w, h, unit = float(m.group(1)), float(m.group(2)), m.group(3)
    if w <= 0 or h <= 0:
        raise ValueError("size dimensions must be positive")
    if unit == "in":
        w, h = w * CM_PER_IN, h * CM_PER_IN
    return w, h, None


def read_profile_fields(path):
    """Read top-level scalar identity fields from a venue profile (no YAML lib)."""
    fields = {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                m = PROFILE_FIELD_RE.match(line)
                if m:
                    value = m.group(2)
                    if " #" in value:
                        value = value.split(" #", 1)[0].rstrip()
                    fields[m.group(1)] = value.strip("'\"")
    except OSError as exc:
        raise IOError("cannot read venue profile %s: %s" % (path, exc))
    if "id" not in fields and "name" not in fields:
        raise IOError("%s does not look like a venue profile (no id:/name:)" % path)
    return fields


def resolve(size_token, orientation):
    w, h, iso = parse_size_token(size_token)
    if iso:
        if orientation is None:
            raise ValueError(
                "--orientation is required with ISO sizes (a0 portrait and a0 "
                "landscape are different posters — check the presenter "
                "instructions)")
        if orientation == "landscape":
            w, h = h, w
    else:
        inferred = "portrait" if w <= h else "landscape"
        if orientation and orientation != inferred:
            raise ValueError(
                "--size %s is %s (width x height as printed) but "
                "--orientation says %s — fix one of them"
                % (size_token, inferred, orientation))
        orientation = inferred
    return {
        "iso": iso,
        "orientation": orientation,
        "w_cm": round(w, 2),
        "h_cm": round(h, 2),
        "w_in": round(w / CM_PER_IN, 2),
        "h_in": round(h / CM_PER_IN, 2),
    }


def invocations(dims):
    scale_factor = min(dims["w_cm"], dims["h_cm"]) / min(ISO_SIZES_CM["a0"])
    bp_scale = round(1.4 * scale_factor, 2)
    if dims["iso"]:
        beamer = ("\\usepackage[size=%s,orientation=%s,scale=%.2f]"
                  "{beamerposter}" % (dims["iso"], dims["orientation"], bp_scale))
        tikz = ("\\documentclass[25pt, %spaper, %s]{tikzposter}"
                % (dims["iso"], dims["orientation"]))
    else:
        beamer = ("\\usepackage[orientation=%s,size=custom,width=%.2f,"
                  "height=%.2f,scale=%.2f]{beamerposter}  %% width/height in cm"
                  % (dims["orientation"], dims["w_cm"], dims["h_cm"], bp_scale))
        tikz = None  # tikzposter has no custom paper size
    return beamer, tikz, scale_factor


def type_scale(scale_factor):
    rows = []
    for name, pt in TYPE_SCALE_A0:
        scaled = max(round(pt * scale_factor), 24 if "Body" in name else 14)
        rows.append({"element": name, "pt": scaled})
    return rows


def board_check(dims, board_token):
    bw, bh, _ = parse_size_token(board_token)
    fits = dims["w_cm"] <= bw + 0.01 and dims["h_cm"] <= bh + 0.01
    return {"board_w_cm": round(bw, 2), "board_h_cm": round(bh, 2), "fits": fits}


def print_markdown(dims, beamer, tikz, scale_factor, board, venue):
    name = dims["iso"].upper() if dims["iso"] else "custom"
    print("# Poster size — %s %s" % (name, dims["orientation"]))
    print()
    if venue:
        print("Venue: %s" % venue.get("name", venue.get("id", "?")))
        url = venue.get("cfp_url") or venue.get("website")
        if url:
            print("RE-VERIFY the poster size, orientation, board dimensions and")
            print("printing rules against the live venue pages before printing:")
            print("%s" % url)
            print("(venue profiles do not encode poster sizes — the presenter")
            print("instructions and your acceptance email are the ground truth).")
        print()
    print("- Printed size: %.2f x %.2f cm  (%.2f x %.2f in), %s"
          % (dims["w_cm"], dims["h_cm"], dims["w_in"], dims["h_in"],
             dims["orientation"]))
    if board:
        verdict = "fits" if board["fits"] else "DOES NOT FIT"
        print("- Venue board %.2f x %.2f cm: poster %s."
              % (board["board_w_cm"], board["board_h_cm"], verdict))
    print()
    print("LaTeX invocations (pick one template):")
    print()
    print("    %s" % beamer)
    if tikz:
        print("    %s" % tikz)
    else:
        print("    (tikzposter supports only a0/a1/a2 paper — for this custom")
        print("     size use beamerposter, or design at A0 and have the print")
        print("     shop scale it, accepting slightly off font sizes)")
    print()
    print("Type scale (linear scale factor %.2f vs A0):" % scale_factor)
    print()
    print("| Element | size (pt) |")
    print("|---------|-----------|")
    for row in type_scale(scale_factor):
        print("| %s | %d |" % (row["element"], row["pt"]))
    print()
    print("- Word budget: target <= %d words total, hard max %d"
          % (WORDS_TARGET, WORDS_MAX))
    print("  (poster_lint.py enforces this).")
    print("- Raster figures need >= 150 dpi at print size: a figure printed")
    print("  %d cm wide needs >= %d px across. Vector PDFs scale freely."
          % (round(dims["w_cm"] / 3),
             round(dims["w_in"] / 3 * 150)))
    print("- Test-print at 25% linear scale (A0 -> ~A4): if you cannot read")
    print("  the body text at arm's length, the audience cannot read the")
    print("  poster from 1.5 m.")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Resolve a poster's exact dimensions, the matching "
        "beamerposter/tikzposter invocations, a scaled font table, and the "
        "word budget. The size must come from the venue's presenter "
        "instructions — never from memory or a venue profile.")
    parser.add_argument("--size", required=True,
                        help="a0|a1|a2 or <W>x<H>in / <W>x<H>cm as printed "
                        "(e.g. 36x48in)")
    parser.add_argument("--orientation", choices=["portrait", "landscape"],
                        default=None,
                        help="required for ISO sizes; for custom WxH it is "
                        "inferred and only checked")
    parser.add_argument("--board", default=None,
                        help="venue's max board size (<W>x<H>in|cm) to check "
                        "the poster fits")
    parser.add_argument("--venue-profile", default=None,
                        help="optional venues/conferences/<id>.yml for venue "
                        "context and the live URL to re-verify against")
    parser.add_argument("--json", action="store_true",
                        help="emit the result as JSON instead of markdown")
    args = parser.parse_args(argv)

    venue = None
    if args.venue_profile:
        try:
            venue = read_profile_fields(args.venue_profile)
        except IOError as exc:
            return fail(str(exc))

    try:
        dims = resolve(args.size, args.orientation)
        board = board_check(dims, args.board) if args.board else None
    except ValueError as exc:
        return fail(str(exc))

    beamer, tikz, scale_factor = invocations(dims)

    if args.json:
        out = {
            "dimensions": dims,
            "beamerposter": beamer,
            "tikzposter": tikz,
            "scale_factor_vs_a0": round(scale_factor, 3),
            "type_scale_pt": type_scale(scale_factor),
            "word_budget": {"target": WORDS_TARGET, "max": WORDS_MAX},
        }
        if board:
            out["board"] = board
        if venue:
            out["venue"] = venue
        json.dump(out, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        print_markdown(dims, beamer, tikz, scale_factor, board, venue)

    if board and not board["fits"]:
        sys.stderr.write(
            "error: poster %.1fx%.1f cm exceeds the venue board %.1fx%.1f cm "
            "— shrink the poster or re-read the presenter instructions\n"
            % (dims["w_cm"], dims["h_cm"],
               board["board_w_cm"], board["board_h_cm"]))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
