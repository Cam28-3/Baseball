from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# -----------------------------
# Domain: neighbor relationships
# -----------------------------

NEIGHBORS: Dict[str, List[str]] = {
    "Q1": ["Q2", "Q4", "T1", "L1"], "Q2": ["Q1", "Q3", "Q5", "T2"], "Q3": ["Q2", "Q6", "T3", "R1"],
    "Q4": ["Q1", "Q5", "Q7", "L2"], "Q5": ["Q2", "Q4", "Q6", "Q8"], "Q6": ["Q3", "Q5", "Q9", "R2"],
    "Q7": ["Q4", "Q8", "L3", "B1"], "Q8": ["Q5", "Q7", "Q9", "B2"], "Q9": ["Q6", "Q8", "R3", "B3"],
    "T1": ["Q1", "Q2", "T2"], "T2": ["Q2", "T1", "T3"], "T3": ["Q2", "Q3", "T2"],
    "L1": ["Q1", "L2"], "L2": ["Q4", "L1", "L3"], "L3": ["Q7", "L2"],
    "R1": ["Q3", "R2"], "R2": ["Q6", "R1", "R3"], "R3": ["Q9", "R2"],
    "B1": ["Q7", "B2"], "B2": ["Q8", "B1", "B3"], "B3": ["Q9", "B2"],
}


ZONES_ORDER: List[List[str]] = [
    ["TL", "T1", "T2", "T3", "TR"],
    ["L1", "Q1", "Q2", "Q3", "R1"],
    ["L2", "Q4", "Q5", "Q6", "R2"],
    ["L3", "Q7", "Q8", "Q9", "R3"],
    ["BL", "B1", "B2", "B3", "BR"],
]

ALL_ZONES = [z for row in ZONES_ORDER for z in row]


# -----------------------------
# Data structures
# -----------------------------

@dataclass(frozen=True)
class PitchEntry:
    pitch_num: int
    target: str
    actual: str
    accuracy: int  # 10 exact, 5 neighbor, 0 miss


@dataclass
class PitchTracker:
    """
    Pure in-app Pitch Tracker state + logic.

    UI should call:
      - set_target(zone)
      - log_pitch(actual_zone)
      - clear_pitch_log()
      - generate_summary()

    Persist later by serializing:
      - target (optional)
      - pitch_counter
      - pitch_log
    """
    target: Optional[str] = None
    pitch_counter: int = 0
    pitch_log: List[PitchEntry] = field(default_factory=list)

    # -----------------------------
    # Core actions
    # -----------------------------

    def set_target(self, zone: str) -> None:
        self._validate_zone(zone)
        self.target = zone

    def log_pitch(self, actual: str) -> PitchEntry:
        self._validate_zone(actual)

        if not self.target:
            raise ValueError("Please set a target first.")

        self.pitch_counter = 1 if self.pitch_counter < 1 else self.pitch_counter + 1
        t = self.target
        a = actual

        accuracy = 0
        if t == a:
            accuracy = 10
        elif self.is_neighbor(t, a):
            accuracy = 5

        entry = PitchEntry(
            pitch_num=self.pitch_counter,
            target=t,
            actual=a,
            accuracy=accuracy,
        )
        self.pitch_log.append(entry)

        # In your Sheets script you clear the target after logging:
        self.target = None

        return entry

    def clear_pitch_log(self) -> None:
        self.pitch_log.clear()
        self.pitch_counter = 0
        self.target = None

    # -----------------------------
    # Helpers
    # -----------------------------

    @staticmethod
    def is_neighbor(target: str, actual: str) -> bool:
        return actual in NEIGHBORS.get(target, [])

    @staticmethod
    def _validate_zone(zone: str) -> None:
        if zone not in ALL_ZONES:
            raise ValueError(f"Invalid zone: {zone}")

    # -----------------------------
    # Summary
    # -----------------------------

    def generate_summary(self) -> Dict:
        """
        Returns a JSON-friendly dict you can render in UI.

        Includes:
          - totals + accuracy %
          - donut counts
          - heatmap grid labels and raw counts
        """
        total = len(self.pitch_log)
        accurate = sum(1 for p in self.pitch_log if p.accuracy == 10)
        close = sum(1 for p in self.pitch_log if p.accuracy == 5)
        miss = total - accurate - close

        accuracy_pct = 0.0
        if total:
            accuracy_pct = (accurate + close) / total * 100.0

        # Heatmap counts by ACTUAL zone (matches your Apps Script)
        counts: Dict[str, int] = {z: 0 for z in ALL_ZONES}
        for p in self.pitch_log:
            if p.actual in counts:
                counts[p.actual] += 1

        def fmt(z: str, v: int) -> str:
            if total:
                return f"{z} ({v}, {(v / total * 100.0):.1f}%)"
            return f"{z} (0,0%)"

        heatmap_labels = [
            [fmt(z, counts[z]) for z in row]
            for row in ZONES_ORDER
        ]
        heatmap_counts = [
            [counts[z] for z in row]
            for row in ZONES_ORDER
        ]

        return {
            "summary": {
                "total_pitches": total,
                "accurate_10": accurate,
                "close_5": close,
                "miss_0": miss,
                "accuracy_pct": round(accuracy_pct, 1),
            },
            "donut": [
                {"label": "Miss", "count": miss},
                {"label": "Close", "count": close},
                {"label": "Accurate", "count": accurate},
            ],
            "heatmap": {
                "zones_order": ZONES_ORDER,
                "labels_grid": heatmap_labels,
                "counts_grid": heatmap_counts,
                "counts_by_zone": counts,  # easy for other UI layouts
            },
            "log": [
                {
                    "pitch_num": p.pitch_num,
                    "target": p.target,
                    "actual": p.actual,
                    "accuracy": p.accuracy,
                }
                for p in self.pitch_log
            ],
        }


# -----------------------------
# Optional: heat color helper
# -----------------------------

def get_heat_color(v: int) -> str:
    if v == 0:
        return "#ffffff"
    if v < 3:
        return "#a3d5ff"
    if v < 6:
        return "#3399ff"
    return "#004c99"
