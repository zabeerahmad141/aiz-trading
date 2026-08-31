"""Create a deterministic offline dataset for backtest development."""

import argparse
from pathlib import Path

from src.backtesting.dataset_store import generate_demo_dataset, save_dataset


parser = argparse.ArgumentParser()
parser.add_argument("--symbol", default="RELIANCE")
parser.add_argument("--rows", type=int, default=500)
parser.add_argument("--output", default="/app/data/historical/RELIANCE-demo.csv")
args = parser.parse_args()

output = save_dataset(
    generate_demo_dataset(args.rows, symbol=args.symbol),
    Path(args.output),
    symbol=args.symbol,
    source="synthetic_development_fixture",
)
print(f"saved={output}")