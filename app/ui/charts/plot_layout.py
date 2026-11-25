"""
Shared layout plan for the 5 x 3 clinical graph pages.

The ``*PageSettings.py`` files describe each Case Presentation section as a
flat list of up to 15 positions laid out row by row across three anatomical
columns. A position whose left *and* right variable names are both empty
(``''``) is an intentionally unused grid cell, kept only so that the graphs
beside it stay anatomically aligned (e.g. hip / knee / ankle columns).

This module turns those lists into an explicit plan that both the on-screen
grid and the PDF export use, so the two stay consistent:

* which cells hold a graph and which are unused;
* which whole rows / columns are empty and can be collapsed;
* which graph is the bottom one in each column (it carries the x labels);
* whether an expected graph has any source data at all.

It is pure Python (no Qt / Matplotlib) so it can be unit tested directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, List, Optional, Tuple

GRID_ROWS = 5
GRID_COLS = 3
DATA_UNAVAILABLE_TEXT = "Data unavailable"


@dataclass(frozen=True)
class GraphSlot:
    """One position in the grid."""

    index: int
    row: int
    col: int
    title: str = ""
    left_var: str = ""
    right_var: str = ""

    @property
    def active(self) -> bool:
        return bool(self.left_var or self.right_var)

    def var_for_limb(self, limb: str) -> str:
        """``limb`` is ``"L"``/``"Left"`` or ``"R"``/``"Right"``."""
        return self.left_var if limb[:1].upper() == "L" else self.right_var


@dataclass
class GridPlan:
    """Resolved layout of one section."""

    rows: int
    cols: int
    slots: List[GraphSlot] = field(default_factory=list)

    @property
    def active_slots(self) -> List[GraphSlot]:
        return [s for s in self.slots if s.active]

    @property
    def unused_slots(self) -> List[GraphSlot]:
        return [s for s in self.slots if not s.active]

    def active_mask(self) -> List[List[bool]]:
        mask = [[False] * self.cols for _ in range(self.rows)]
        for s in self.active_slots:
            mask[s.row][s.col] = True
        return mask

    @property
    def occupied_rows(self) -> List[int]:
        return sorted({s.row for s in self.active_slots})

    @property
    def occupied_cols(self) -> List[int]:
        return sorted({s.col for s in self.active_slots})

    def bottom_row_by_col(self) -> Dict[int, int]:
        """Lowest occupied row of every column; that graph shows the x labels."""
        out: Dict[int, int] = {}
        for s in self.active_slots:
            out[s.col] = max(out.get(s.col, -1), s.row)
        return out

    def shows_x_labels(self, slot: GraphSlot) -> bool:
        return self.bottom_row_by_col().get(slot.col) == slot.row

    def compacted(self) -> "GridPlan":
        """Reflow: drop unused placeholders and fill the grid row by row.

        Valid graphs keep their relative order and their original ``index``
        (used to look up titles, limits and ticks in the settings lists);
        only ``row``/``col`` change, so only the last row can be partial.
        """
        slots = [
            GraphSlot(s.index, pos // self.cols, pos % self.cols, s.title, s.left_var, s.right_var)
            for pos, s in enumerate(self.active_slots)
        ]
        return GridPlan(rows=self.rows, cols=self.cols, slots=slots)


def _item(values: Optional[List], idx: int, default=""):
    if not values or idx >= len(values):
        return default
    value = values[idx]
    return default if value is None else value


def build_grid_plan(settings, rows: int = GRID_ROWS, cols: int = GRID_COLS) -> GridPlan:
    """Build the plan for a ``PageSettings`` (only ``left_names``,
    ``right_names`` and ``titles`` are read)."""
    left = list(getattr(settings, "left_names", None) or [])
    right = list(getattr(settings, "right_names", None) or [])
    titles = list(getattr(settings, "titles", None) or [])
    capacity = rows * cols
    count = min(max(len(left), len(right)), capacity)
    slots = []
    for idx in range(capacity):
        l_var = str(_item(left, idx)).strip() if idx < count else ""
        r_var = str(_item(right, idx)).strip() if idx < count else ""
        title = str(_item(titles, idx)).strip()
        slots.append(GraphSlot(idx, idx // cols, idx % cols, title, l_var, r_var))
    return GridPlan(rows=rows, cols=cols, slots=slots)


def trial_limb(trial_key: str) -> str:
    """``"L3"`` -> ``"L"``; ``"R10"`` -> ``"R"``."""
    return trial_key[:1].upper()


def availability_message(
    slot: GraphSlot,
    trials: Dict[str, object],
    limbs: Iterable[str],
    has_data: Callable[[object, str], bool],
) -> Optional[str]:
    """Return a "data unavailable" note for an expected graph, or ``None``.

    ``trials`` maps trial keys (``L1`` ... ``R10``) to *loaded* trial data,
    regardless of which pills are selected, so that deselecting trials never
    looks like missing data. ``has_data(trial, var)`` tells whether a trial
    really contains the variable. A limb with no loaded trials at all is not
    reported (there is nothing to look for).
    """
    if not slot.active:
        return None
    missing: List[str] = []
    checked = 0
    for limb in limbs:
        var = slot.var_for_limb(limb)
        limb_trials = [t for k, t in trials.items() if trial_limb(k) == limb and t is not None]
        if not limb_trials:
            continue
        checked += 1
        if not var or not any(has_data(t, var) for t in limb_trials):
            missing.append(limb)
    if not checked or not missing:
        return None
    if len(missing) == checked:
        return DATA_UNAVAILABLE_TEXT
    names = {"L": "Left", "R": "Right"}
    return f"{' / '.join(names.get(m, m) for m in missing)} {DATA_UNAVAILABLE_TEXT.lower()}"


def limbs_for_side(side: str) -> Tuple[str, ...]:
    return {"L": ("L",), "R": ("R",)}.get(side, ("L", "R"))
