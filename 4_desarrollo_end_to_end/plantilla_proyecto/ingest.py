"""Ingesta + limpieza mínima para la plantilla E2E."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def clean_sales(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    frame["unidades"] = pd.to_numeric(frame["unidades"], errors="coerce")
    frame["precio_unitario"] = pd.to_numeric(frame["precio_unitario"], errors="coerce")
    ok = frame["unidades"].notna() & (frame["unidades"] > 0) & (frame["precio_unitario"] > 0)
    clean = frame.loc[ok].copy()
    clean["importe"] = clean["unidades"] * clean["precio_unitario"]
    return clean


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    clean = clean_sales(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    clean.to_csv(args.output, index=False)
    print(f"Wrote {len(clean)} rows -> {args.output}")


if __name__ == "__main__":
    main()
