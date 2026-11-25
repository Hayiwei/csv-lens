"""Rebuild a small synthetic dataset with known data-quality issues."""

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def make_sample() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    size = 240
    price = rng.uniform(4, 80, size).round(2)
    quantity = rng.integers(1, 5, size)
    frame = pd.DataFrame({
        "order_id": [f"ORD-{i + 1:04d}" for i in range(size)],
        "date": pd.date_range("2026-01-01", periods=size, freq="6h").strftime("%Y-%m-%d"),
        "category": rng.choice(["Books", "Coffee", "Stationery", "Accessories"], size),
        "channel": rng.choice(["Online", "In-store"], size, p=[0.65, 0.35]),
        "city": rng.choice(["Harbor", "Hillview", "Riverside"], size),
        "unit_price": price,
        "quantity": quantity,
        "order_total": np.round(price * quantity, 2),
    })
    frame.loc[range(15, 26), "city"] = np.nan
    frame.loc[range(30, 39), "unit_price"] = np.nan
    frame.loc[range(45, 50), "channel"] = np.nan
    return pd.concat([frame, frame.iloc[:8]], ignore_index=True)


if __name__ == "__main__":
    target = ROOT / "data" / "sample_orders.csv"
    target.parent.mkdir(parents=True, exist_ok=True)
    make_sample().to_csv(target, index=False)
    print(f"Wrote {target.name}: 248 synthetic rows, including 8 extra copies.")
