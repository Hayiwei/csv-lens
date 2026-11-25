"""Render a static report preview from the same sample used by the app."""

from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from csv_lens.core import load_csv, inspect_frame


def main():
    frame = load_csv((ROOT / "data" / "sample_orders.csv").read_bytes()).frame
    report = inspect_frame(frame)
    navy, teal, muted = "#19334A", "#117C83", "#526778"
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "text.color": navy})
    fig = plt.figure(figsize=(12, 7.2), facecolor="white")
    fig.text(.055, .92, "CSV LENS", color=teal, size=12, weight="bold")
    fig.text(.055, .855, "A closer look at your data.", size=26, weight="bold")
    fig.text(.055, .805, "Sample report  /  synthetic shop orders", color=muted, size=11)
    stats = [
        ("ROWS", str(report["rows"])), ("COLUMNS", str(report["columns"])),
        ("MISSING CELLS", f'{report["missing_pct"]:.1f}%'), ("DUPLICATE ROWS", str(report["duplicate_rows"])),
    ]
    for i, (label, value) in enumerate(stats):
        x = .055 + i * .228
        fig.add_artist(FancyBboxPatch(
            (x, .625), .205, .13, boxstyle="round,pad=0.009,rounding_size=0.012",
            transform=fig.transFigure, facecolor="#F2F6F8", edgecolor="#E2EAF0",
        ))
        fig.text(x + .015, .715, label, size=8.5, color=muted, weight="bold")
        fig.text(x + .015, .655, value, size=24, weight="bold")
    left = fig.add_axes((.09, .16, .37, .35))
    fields = report["column_profiles"]
    left.barh([x["column"] for x in fields], [x["missing_pct"] for x in fields], color=teal, height=.56)
    left.invert_yaxis()
    left.set(xlim=(0, 6), xlabel="Missing values (%)", title="Completeness by column")
    right = fig.add_axes((.59, .16, .35, .35))
    right.hist(frame["order_total"], bins=17, color=teal, edgecolor="white", linewidth=1)
    right.set(xlabel="Order total (synthetic currency units)", ylabel="Rows", title="Order value distribution")
    for ax in (left, right):
        ax.spines[["top", "right"]].set_visible(False)
        ax.spines[["left", "bottom"]].set_color("#D9E3E9")
        ax.tick_params(colors=muted, labelsize=9)
        ax.title.set_fontsize(12)
        ax.title.set_weight("bold")
        ax.set_axisbelow(True)
        ax.grid(axis="x" if ax is left else "y", color="#EAF0F3")
    fig.text(.055, .045, "CSV Lens  /  Counts cover all 248 rows. This is a generated report preview, not an app screenshot.", color=muted, size=8)
    target = ROOT / "docs" / "sample-report.png"
    target.parent.mkdir(exist_ok=True)
    fig.savefig(target, dpi=160, facecolor="white")
    plt.close(fig)
    print(f"Wrote {target.name}")


if __name__ == "__main__":
    main()
