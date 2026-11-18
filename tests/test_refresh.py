"""Tests for safe source-data refresh behaviour."""

from io import BytesIO
from pathlib import Path
import sys

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ghana_banking.data import refresh


def monthly_csv(latest="01/02/2026"):
    frame = pd.DataFrame({
        "Name of Series": ["01/01/2026", latest],
        "Monetary Policy Rate (%)": [15, 15],
        "Consumer Price Index, All Items": [100, 101],
        "USD Exchange Rate, monthly averages": [10, 10.1],
        "Total Liquidity (M2+)": [1000, 1010],
        "Gold Price (Realised Gold Price)": [2000, 2010],
        "Return on Assets": [2.0, 2.1],
        "Non Performing Loan Ratio": [15.0, 14.9],
        "Capital Adequacy Ratio": [18.0, 18.1],
    })
    return frame.to_csv(index=False).encode("utf-8")


def gdp_csv(latest="2026Q1"):
    frame = pd.DataFrame({
        "Name of Series": ["2025Q4", latest],
        "Gross Domestic Product (GDP), production, real": [50000, 51000],
    })
    return frame.to_csv(index=False).encode("utf-8")


def test_parse_monthly_refresh_payload_validates_required_schema():
    frame, latest = refresh._parse_monthly(monthly_csv())
    assert len(frame) == 2
    assert latest == pd.Timestamp("2026-02-01")


def test_parse_gdp_refresh_payload_preserves_quarter():
    frame, latest = refresh._parse_gdp(gdp_csv())
    assert len(frame) == 2
    assert latest == pd.Period("2026Q1", freq="Q")


def test_refresh_rejects_stale_download_without_changing_local_files(
    tmp_path, monkeypatch
):
    raw = tmp_path / "raw"
    raw.mkdir()
    monthly_path = raw / refresh.MONTHLY_FILE
    gdp_path = raw / refresh.GDP_FILE
    monthly_path.write_bytes(monthly_csv("01/03/2026"))
    gdp_path.write_bytes(gdp_csv("2026Q1"))
    original_monthly = monthly_path.read_bytes()
    original_gdp = gdp_path.read_bytes()

    payloads = iter([monthly_csv("01/02/2026"), gdp_csv("2026Q1")])
    monkeypatch.setattr(refresh, "_download_csv", lambda *args, **kwargs: next(payloads))

    with pytest.raises(ValueError, match="stale"):
        refresh.refresh_source_data(
            "https://example.test/monthly.csv",
            "https://example.test/gdp.csv",
            raw_data_path=str(raw),
        )

    assert monthly_path.read_bytes() == original_monthly
    assert gdp_path.read_bytes() == original_gdp


def test_refresh_updates_both_files_after_validation(tmp_path, monkeypatch):
    raw = tmp_path / "raw"
    raw.mkdir()
    payloads = iter([monthly_csv(), gdp_csv()])
    monkeypatch.setattr(refresh, "_download_csv", lambda *args, **kwargs: next(payloads))

    result = refresh.refresh_source_data(
        "https://example.test/monthly.csv",
        "https://example.test/gdp.csv",
        raw_data_path=str(raw),
    )

    assert result["monthly_latest"] == "2026-02-01"
    assert result["gdp_latest"] == "2026Q1"
    assert (raw / refresh.MONTHLY_FILE).exists()
    assert (raw / refresh.GDP_FILE).exists()
