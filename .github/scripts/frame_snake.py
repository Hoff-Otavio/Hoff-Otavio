"""Wrap the Platane/snk SVG in the same dark panel used by the other profile SVGs.

Usage: frame_snake.py <snake.svg> <out.svg> [calendar.json]

calendar.json is the GraphQL contributionCalendar response (totalContributions and
weeks.firstDay). With it, the panel gets the total, month and weekday labels and a
Less/More legend, like the native contribution graph. Without it, only the panel.
"""
import json
import re
import sys

CELL = 16  # snk grid pitch: 12px cell + 4px gap, cell drawn at col*16+2
W = 880
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace"
MUTED = "#64748b"
TEXT = "#e2e8f0"
ACCENT = "#f97316"
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()


def text(x, y, value, fill=MUTED, size=10, anchor="start", spacing=None):
    extra = f' letter-spacing="{spacing}"' if spacing else ""
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" font-family="{MONO}" '
        f'font-size="{size}"{extra} fill="{fill}">{value}</text>'
    )


def load_calendar(path):
    try:
        data = json.load(open(path, encoding="utf-8"))
        cal = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
        return cal["totalContributions"], [w["firstDay"] for w in cal["weeks"]]
    except Exception as exc:  # labels are optional; never break the snake
        print(f"calendar ignored: {exc}", file=sys.stderr)
        return None, []


src, dst = sys.argv[1], sys.argv[2]
total, weeks = load_calendar(sys.argv[3]) if len(sys.argv) > 3 else (None, [])
snake = open(src, encoding="utf-8").read()

m = re.match(r"\s*<svg([^>]*)>", snake)
if not m:
    sys.exit("snake svg: opening tag not found")
view_box = re.search(r'viewBox="([^"]+)"', m.group(1)).group(1)
vb_x, vb_y, vb_w, vb_h = (float(v) for v in view_box.split())
cols = len(re.findall(r'<rect class="c[^>]* y="2"', snake))
levels = [re.search(rf"--c{i}:(#[0-9a-fA-F]+)", snake) for i in range(5)]
levels = [lv.group(1) for lv in levels if lv]

# Snake area placement: leave a left gutter for weekday labels.
X0, Y0 = 48.0, 50.0
inner_w = W - X0 - 16
s = inner_w / vb_w
inner_h = vb_h * s


def ox(vx):
    return X0 + (vx - vb_x) * s


def oy(vy):
    return Y0 + (vy - vb_y) * s


grid_bottom = oy(7 * CELL)
legend_y = grid_bottom + 20
H = round(max(Y0 + inner_h, legend_y + 26))

parts = [
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
    f'role="img" aria-label="Snake eating the GitHub contribution graph">',
    f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="16" fill="#0d1526" stroke="#24324f"/>',
    text(24, 37, "CONTRIBUTIONS", fill=ACCENT, size=11, spacing=1.5),
]
if total is not None:
    parts.append(
        f'<text x="{W - 24}" y="37" text-anchor="end" font-family="{MONO}" font-size="11" '
        f'letter-spacing="1.5" fill="{MUTED}"><tspan fill="{TEXT}">{total}</tspan> IN THE LAST YEAR</text>'
    )

if weeks and cols:
    # Align from the right: the last week is the last column of the snake grid.
    weeks = weeks[-cols:]
    offset = cols - len(weeks)
    marks = []
    for i, day in enumerate(weeks):
        month = int(day[5:7])
        if i == 0 or month != int(weeks[i - 1][5:7]):
            marks.append((offset + i, MONTHS[month - 1]))
    # Like GitHub: drop a label that would collide with the next one.
    marks = [mk for k, mk in enumerate(marks) if k + 1 == len(marks) or marks[k + 1][0] - mk[0] >= 3]
    for col, name in marks:
        parts.append(text(ox(col * CELL + 2), oy(-6), name))
    for row, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        parts.append(text(ox(0) - 8, oy(row * CELL + 8) + 3.5, name, anchor="end"))

if len(levels) == 5:
    size, gap = 10, 3
    x = W - 24 - 32  # room for "More"
    parts.append(text(W - 24, legend_y + 9, "More", anchor="end"))
    for color in reversed(levels):
        x -= size
        parts.append(f'<rect x="{x:.1f}" y="{legend_y:.1f}" width="{size}" height="{size}" rx="2" fill="{color}"/>')
        x -= gap
    parts.append(text(x - 4, legend_y + 9, "Less", anchor="end"))

parts.append(f'<svg x="{X0}" y="{Y0}" width="{inner_w:.1f}" height="{inner_h:.1f}" viewBox="{view_box}">')
open(dst, "w", encoding="utf-8").write("".join(parts) + snake[m.end():] + "</svg>")
