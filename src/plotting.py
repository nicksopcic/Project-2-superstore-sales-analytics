"""Chart palette and Matplotlib styling shared by the notebooks and the dashboard.

Colour is assigned by the job it does rather than by position in a loop:

  categorical  identity, for regions/categories/segments. Fixed slot order, never cycled.
  sequential   magnitude, one hue light to dark.
  diverging    polarity, two hues either side of a neutral grey. Used for profit, where
               the sign is the point.

The categorical slots below were validated for colour-vision deficiency separation before
use: worst adjacent pair 9.1 dE for the four-slot set, and 9.2 dE all-pairs for the
three-slot set used in scatter plots. Aqua and yellow sit below 3:1 contrast against the
chart surface, so every chart that uses them carries direct labels or a table underneath.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt

from src.utils import FIGURES_DIR

# Categorical slots in fixed order. A fifth series folds into "Other" rather than
# taking a generated hue.
CATEGORICAL = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]

REGION_COLORS = {
    "West": CATEGORICAL[0],
    "East": CATEGORICAL[1],
    "Central": CATEGORICAL[2],
    "South": CATEGORICAL[3],
}
CATEGORY_COLORS = {
    "Technology": CATEGORICAL[0],
    "Office Supplies": CATEGORICAL[1],
    "Furniture": CATEGORICAL[2],
}
SEGMENT_COLORS = {
    "Consumer": CATEGORICAL[0],
    "Corporate": CATEGORICAL[1],
    "Home Office": CATEGORICAL[2],
}

# Diverging poles for profit. Blue earns, red loses, grey is the zero line.
PROFIT_POSITIVE = "#2a78d6"
PROFIT_NEGATIVE = "#d03b3b"
NEUTRAL = "#f0efec"

SEQUENTIAL = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#2a78d6", "#1c5cab", "#104281"]

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_MUTED = "#52514e"
GRID = "#e3e2df"


def apply_style() -> None:
    """Recessive chrome, readable ink, no chart junk."""
    mpl.rcParams.update(
        {
            "figure.facecolor": SURFACE,
            "axes.facecolor": SURFACE,
            "savefig.facecolor": SURFACE,
            "figure.dpi": 110,
            "savefig.dpi": 150,
            "savefig.bbox": "tight",
            "font.size": 10,
            "text.color": INK,
            "axes.labelcolor": INK_MUTED,
            "axes.edgecolor": GRID,
            "axes.titlecolor": INK,
            "axes.titlesize": 12,
            "axes.titleweight": "semibold",
            "axes.titlelocation": "left",
            "axes.titlepad": 12,
            "axes.grid": True,
            "axes.axisbelow": True,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "grid.color": GRID,
            "grid.linewidth": 0.8,
            "xtick.color": INK_MUTED,
            "ytick.color": INK_MUTED,
            "xtick.labelcolor": INK_MUTED,
            "ytick.labelcolor": INK_MUTED,
            "legend.frameon": False,
            "lines.linewidth": 2.0,
            "lines.markersize": 5,
            "axes.prop_cycle": mpl.cycler(color=CATEGORICAL),
        }
    )


def profit_colors(values) -> list[str]:
    """One colour per bar, by the sign of the value. Polarity is the message."""
    return [PROFIT_NEGATIVE if v < 0 else PROFIT_POSITIVE for v in values]


def currency(value: float, _pos: int | None = None) -> str:
    """Axis tick formatter. $1.2M, $340K, $980."""
    for threshold, suffix in ((1_000_000, "M"), (1_000, "K")):
        if abs(value) >= threshold:
            return f"${value / threshold:,.1f}{suffix}"
    return f"${value:,.0f}"


def save_figure(fig: plt.Figure, name: str, directory: Path | None = None) -> Path:
    """Write a figure to reports/figures/ so the README and the write-up can embed it."""
    target_dir = directory or FIGURES_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / f"{name}.png"
    fig.savefig(path)
    return path
