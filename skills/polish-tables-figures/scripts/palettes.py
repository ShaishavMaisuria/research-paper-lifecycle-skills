#!/usr/bin/env python3
"""Colorblind-safe palettes for paper figures, plus a CVD-safety checker.

Subcommands:
  list                       list bundled palettes
  show NAME --format FMT     emit a palette as latex | pgfplots | matplotlib | hex
  check [HEX ...]            simulate color-vision deficiencies for a set of
                             colors (or --palette NAME) and flag confusable
                             pairs; also checks grayscale-print separation

CVD simulation uses the Machado, Oliveira & Fernandes (2009) severity-1.0
matrices in linear sRGB; pair distance is CIE76 deltaE in Lab (D65).
Stdlib only. No network.

Exit codes: 0 = ok / no confusable pairs, 1 = confusable pairs found
(check mode), 2 = bad arguments.
"""

import argparse
import json
import sys

# ---------------------------------------------------------------------------
# bundled palettes (qualitative, colorblind-safe)
# ---------------------------------------------------------------------------
# Okabe & Ito (2008), "Color Universal Design" — the de-facto standard
# 8-color qualitative palette for scientific figures.
# Paul Tol (SRON technical note, https://sronpersonalpages.nl/~pault/) —
# bright / muted / light qualitative schemes + high-contrast.

PALETTES = {
    "okabe-ito": [
        ("black", "000000"), ("orange", "E69F00"), ("skyblue", "56B4E9"),
        ("bluishgreen", "009E73"), ("yellow", "F0E442"), ("blue", "0072B2"),
        ("vermillion", "D55E00"), ("reddishpurple", "CC79A7"),
    ],
    "tol-bright": [
        ("blue", "4477AA"), ("cyan", "66CCEE"), ("green", "228833"),
        ("yellow", "CCBB44"), ("red", "EE6677"), ("purple", "AA3377"),
        ("grey", "BBBBBB"),
    ],
    "tol-muted": [
        ("indigo", "332288"), ("cyan", "88CCEE"), ("teal", "44AA99"),
        ("green", "117733"), ("olive", "999933"), ("sand", "DDCC77"),
        ("rose", "CC6677"), ("wine", "882255"), ("purple", "AA4499"),
    ],
    "tol-light": [
        ("lightblue", "77AADD"), ("lightcyan", "99DDFF"), ("mint", "44BB99"),
        ("pear", "BBCC33"), ("olive", "AAAA00"), ("lightyellow", "EEDD88"),
        ("orange", "EE8866"), ("pink", "FFAABB"), ("palegrey", "DDDDDD"),
    ],
    "tol-high-contrast": [
        ("blue", "004488"), ("yellow", "DDAA33"), ("red", "BB5566"),
    ],
}

PREFIX = {"okabe-ito": "oi", "tol-bright": "tb", "tol-muted": "tm",
          "tol-light": "tl", "tol-high-contrast": "thc"}

MARKS = ["*", "square*", "triangle*", "diamond*", "pentagon*", "o", "x", "+", "asterisk"]
DASHES = ["solid", "dashed", "dotted", "dashdotted", "densely dashed",
          "densely dotted", "loosely dashed", "loosely dotted", "solid"]

# Machado, Oliveira & Fernandes (2009), severity 1.0, linear-RGB matrices.
CVD_MATRICES = {
    "protanopia": [
        (0.152286, 1.052583, -0.204868),
        (0.114503, 0.786281, 0.099216),
        (-0.003882, -0.048116, 1.051998),
    ],
    "deuteranopia": [
        (0.367322, 0.860646, -0.227968),
        (0.280085, 0.672501, 0.047413),
        (-0.011820, 0.042940, 0.968881),
    ],
    "tritanopia": [
        (1.255528, -0.076749, -0.178779),
        (-0.078411, 0.930809, 0.147602),
        (0.004733, 0.691367, 0.303900),
    ],
}


# ---------------------------------------------------------------------------
# color math (sRGB -> linear -> XYZ -> Lab, CIE76 deltaE)
# ---------------------------------------------------------------------------

def parse_hex(s):
    t = s.strip().lstrip("#")
    if len(t) == 3:
        t = "".join(c * 2 for c in t)
    if len(t) != 6 or any(c not in "0123456789abcdefABCDEF" for c in t):
        raise ValueError("not a hex color: %r" % s)
    return tuple(int(t[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def to_srgb(c):
    c = min(max(c, 0.0), 1.0)
    return 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055


def rgb_to_lab(rgb):
    r, g, b = (to_linear(c) for c in rgb)
    x = 0.4124 * r + 0.3576 * g + 0.1805 * b
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    z = 0.0193 * r + 0.1192 * g + 0.9505 * b
    xn, yn, zn = 0.95047, 1.0, 1.08883

    def f(t):
        return t ** (1 / 3) if t > (6 / 29) ** 3 else t / (3 * (6 / 29) ** 2) + 4 / 29

    fx, fy, fz = f(x / xn), f(y / yn), f(z / zn)
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def delta_e(lab1, lab2):
    return sum((a - b) ** 2 for a, b in zip(lab1, lab2)) ** 0.5


def simulate_cvd(rgb, kind):
    lin = [to_linear(c) for c in rgb]
    mat = CVD_MATRICES[kind]
    out = [sum(m * c for m, c in zip(row, lin)) for row in mat]
    return tuple(to_srgb(c) for c in out)


def lightness(rgb):
    """L* of the grayscale rendering (relative luminance -> Lab L)."""
    return rgb_to_lab(rgb)[0]


# ---------------------------------------------------------------------------
# emit formats
# ---------------------------------------------------------------------------

def cname(palette, name):
    return PREFIX.get(palette, "pal") + name[0].upper() + name[1:]


def emit_latex(palette, colors):
    lines = ["%% %s — colorblind-safe palette (xcolor)" % palette]
    for name, hexv in colors:
        lines.append("\\definecolor{%s}{HTML}{%s}" % (cname(palette, name), hexv))
    return "\n".join(lines)


def emit_pgfplots(palette, colors):
    lines = [emit_latex(palette, colors), "",
             "%% redundant encoding: distinct color + mark + dash per series",
             "\\pgfplotscreateplotcyclelist{%s}{%%" % palette]
    for i, (name, _hexv) in enumerate(colors):
        lines.append("  {%s, mark=%s, %s}%s" % (
            cname(palette, name), MARKS[i % len(MARKS)],
            DASHES[i % len(DASHES)], "," if i < len(colors) - 1 else ""))
    lines.append("}")
    lines.append("%% then: \\begin{axis}[cycle list name=%s]" % palette)
    return "\n".join(lines)


def emit_matplotlib(palette, colors):
    var = palette.upper().replace("-", "_")
    hexes = ", ".join('"#%s"' % h for _n, h in colors)
    return "\n".join([
        "# %s — colorblind-safe palette" % palette,
        "from cycler import cycler",
        "import matplotlib.pyplot as plt",
        "%s = [%s]" % (var, hexes),
        'plt.rcParams["axes.prop_cycle"] = cycler(color=%s)' % var,
    ])


def emit_hex(palette, colors):
    return "\n".join("#%s  %s" % (h, n) for n, h in colors)


EMITTERS = {"latex": emit_latex, "pgfplots": emit_pgfplots,
            "matplotlib": emit_matplotlib, "hex": emit_hex}


# ---------------------------------------------------------------------------
# check
# ---------------------------------------------------------------------------

def run_check(named_colors, threshold, warn_threshold, gray_threshold,
              require_grayscale, as_json):
    rgbs = [(label, parse_hex(h)) for label, h in named_colors]
    conditions = ["normal", "protanopia", "deuteranopia", "tritanopia"]
    problems, warnings = [], []
    for i in range(len(rgbs)):
        for j in range(i + 1, len(rgbs)):
            (la, ca), (lb, cb) = rgbs[i], rgbs[j]
            for cond in conditions:
                a = ca if cond == "normal" else simulate_cvd(ca, cond)
                b = cb if cond == "normal" else simulate_cvd(cb, cond)
                de = delta_e(rgb_to_lab(a), rgb_to_lab(b))
                entry = {"pair": [la, lb], "condition": cond,
                         "delta_e": round(de, 1)}
                if de < threshold:
                    problems.append(entry)
                elif de < warn_threshold:
                    warnings.append(entry)
            dl = abs(lightness(ca) - lightness(cb))
            if dl < gray_threshold:
                entry = {"pair": [la, lb], "condition": "grayscale-print",
                         "delta_e": round(dl, 1)}
                (problems if require_grayscale else warnings).append(entry)

    if as_json:
        json.dump({"colors": [{"label": l, "hex": h} for l, h in named_colors],
                   "confusable": problems, "borderline": warnings,
                   "thresholds": {"fail": threshold, "warn": warn_threshold,
                                  "grayscale": gray_threshold}},
                  sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        print("Checked %d colors (%d pairs) under: %s + grayscale-print."
              % (len(rgbs), len(rgbs) * (len(rgbs) - 1) // 2,
                 ", ".join(conditions)))
        if not problems and not warnings:
            print("OK: no confusable or borderline pairs "
                  "(deltaE fail<%g, warn<%g, grayscale dL*<%g)."
                  % (threshold, warn_threshold, gray_threshold))
        for e in problems:
            print("CONFUSABLE  %-22s %-16s deltaE=%.1f"
                  % (" vs ".join(e["pair"]), e["condition"], e["delta_e"]))
        for e in warnings:
            print("borderline  %-22s %-16s deltaE=%.1f"
                  % (" vs ".join(e["pair"]), e["condition"], e["delta_e"]))
        if problems:
            print("\nVerdict: NOT SAFE — drop or replace one color in each "
                  "confusable pair (see references/color-accessibility.md).")
        else:
            print("\nVerdict: SAFE at the fail threshold"
                  + (" (borderline pairs above — add markers/line styles as "
                     "redundant encoding)." if warnings else "."))
    return 1 if problems else 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Colorblind-safe palettes (Okabe-Ito, Paul Tol) for paper "
                    "figures: list/emit as LaTeX, pgfplots, matplotlib, or hex, "
                    "and check arbitrary colors for CVD + grayscale safety.")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("list", help="list bundled palettes")

    p_show = sub.add_parser("show", help="emit a palette in a given format")
    p_show.add_argument("name", help="palette name (see 'list')")
    p_show.add_argument("--format", default="hex", choices=sorted(EMITTERS),
                        help="output format (default: hex)")

    p_check = sub.add_parser(
        "check", help="flag color pairs confusable under CVD / grayscale")
    p_check.add_argument("colors", nargs="*",
                         help="hex colors, e.g. E69F00 '#56B4E9'")
    p_check.add_argument("--palette", help="check a bundled palette instead")
    p_check.add_argument("--threshold", type=float, default=12.0,
                         help="deltaE below this = confusable (default: 12)")
    p_check.add_argument("--warn-threshold", type=float, default=20.0,
                         help="deltaE below this = borderline (default: 20)")
    p_check.add_argument("--gray-threshold", type=float, default=10.0,
                         help="L* gap below this = grayscale-unsafe (default: 10)")
    p_check.add_argument("--require-grayscale", action="store_true",
                         help="treat grayscale-print collisions as failures, "
                              "not warnings")
    p_check.add_argument("--json", action="store_true",
                         help="machine-readable output")

    args = parser.parse_args(argv)
    if not args.cmd:
        parser.print_help()
        return 2

    if args.cmd == "list":
        for name, colors in PALETTES.items():
            print("%-18s %d colors: %s" % (name, len(colors),
                                           " ".join("#" + h for _n, h in colors)))
        return 0

    if args.cmd == "show":
        if args.name not in PALETTES:
            sys.stderr.write("error: unknown palette %r (available: %s)\n"
                             % (args.name, ", ".join(sorted(PALETTES))))
            return 2
        print(EMITTERS[args.format](args.name, PALETTES[args.name]))
        return 0

    # check
    if args.palette:
        if args.palette not in PALETTES:
            sys.stderr.write("error: unknown palette %r (available: %s)\n"
                             % (args.palette, ", ".join(sorted(PALETTES))))
            return 2
        named = [(n, h) for n, h in PALETTES[args.palette]]
    elif args.colors:
        try:
            named = [(c.lstrip("#").upper(), c) for c in args.colors]
            for _label, h in named:
                parse_hex(h)
        except ValueError as exc:
            sys.stderr.write("error: %s\n" % exc)
            return 2
    else:
        sys.stderr.write("error: pass hex colors or --palette NAME\n")
        return 2
    if len(named) < 2:
        sys.stderr.write("error: need at least 2 colors to compare\n")
        return 2
    return run_check(named, args.threshold, args.warn_threshold,
                     args.gray_threshold, args.require_grayscale, args.json)


if __name__ == "__main__":
    sys.exit(main())
