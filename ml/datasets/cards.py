"""Generate a dataset card next to every CSV the builder writes."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import pandas as pd


def write_card(
    csv_path: Path,
    *,
    title: str,
    source: str,
    assumptions: Iterable[str],
    production_replacement: str,
    extra_notes: Iterable[str] = (),
    df: pd.DataFrame | None = None,
) -> Path:
    """Write a Markdown dataset card next to the CSV.

    A dataset card is the dataset equivalent of a model card. It documents
    provenance, what the labels mean, and what would replace this in production.
    """
    lines: list[str] = []
    lines.append(f"# Dataset card: {title}")
    lines.append("")
    lines.append(f"Generated: {datetime.now(timezone.utc).isoformat()}")
    lines.append("")
    lines.append("## Source")
    lines.append(source)
    lines.append("")
    if df is not None:
        lines.append("## Shape")
        lines.append(f"- Rows: {len(df)}")
        lines.append(f"- Columns: {len(df.columns)}")
        if "landslide_occurred" in df.columns:
            pos = int(df["landslide_occurred"].sum())
            neg = len(df) - pos
            lines.append(f"- Positive labels (landslide=1): {pos}")
            lines.append(f"- Negative labels (landslide=0): {neg}")
            if neg > 0:
                lines.append(f"- Class balance: {pos / len(df):.1%} positive")
        lines.append("")
    lines.append("## Assumptions")
    for a in assumptions:
        lines.append(f"- {a}")
    lines.append("")
    lines.append("## Production replacement")
    lines.append(production_replacement)
    lines.append("")
    if extra_notes:
        lines.append("## Notes")
        for n in extra_notes:
            lines.append(f"- {n}")
        lines.append("")
    lines.append("## Hard rule")
    lines.append("")
    lines.append("No number in this dataset or any model trained on it may be "
                 "presented as a real forecast for any real location. "
                 "Predictions are decision-support only.")
    lines.append("")
    out = csv_path.with_name("dataset_card.md")
    out.write_text("\n".join(lines), encoding="utf-8")
    return out
