import pytest

from src.backtesting.dataset_store import generate_demo_dataset, load_dataset, save_dataset


def test_demo_dataset_round_trips_with_manifest(tmp_path):
    path = save_dataset(
        generate_demo_dataset(60),
        tmp_path / "reliance.csv",
        symbol="RELIANCE",
        source="test_fixture",
    )
    candles, manifest = load_dataset(path)
    assert len(candles) == 60
    assert manifest["symbol"] == "RELIANCE"
    assert manifest["source"] == "test_fixture"


def test_dataset_rejects_invalid_price_range(tmp_path):
    candles = generate_demo_dataset(60)
    candles.loc[0, "low"] = candles.loc[0, "high"] + 1
    with pytest.raises(ValueError, match="low must be"):
        save_dataset(candles, tmp_path / "invalid.csv", symbol="RELIANCE", source="test")