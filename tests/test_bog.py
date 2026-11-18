"""Tests for the Bank of Ghana financial soundness connector."""

from pathlib import Path
import sys

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ghana_banking.data import bog


def fsi_metadata():
    return {
        "variables": [
            {
                "code": "Month",
                "text": "Month",
                "values": ["2024M01", "2024M02"],
                "valueTexts": ["2024M01", "2024M02"],
                "time": True,
            },
            {
                "code": "Indicator",
                "text": "Indicator",
                "values": ["CAR", "CDR", "CLASTL", "CLATA", "NPL", "OC_I", "ROA", "ROE", "TCGIR"],
                "valueTexts": [
                    "Capital adequacy ratio",
                    "Credit to Deposits",
                    "Core Liquid Assets to Short-term Liabilities",
                    "Core Liquid Assets to Total Assets",
                    "Non-Performing Loans",
                    "Operational Cost/Income",
                    "Return on Assets - Before Tax",
                    "Return on Equity - After Tax",
                    "Total Cost to Gross Income Ratio",
                ],
            },
        ]
    }


def fsi_csv(months=12):
    periods = pd.period_range("2024-01", periods=months, freq="M")
    rows = []
    for i, period in enumerate(periods):
        label = "{}M{:02d}".format(period.year, period.month)
        rows.extend([
            {"Month": label, "Indicator": "CAR", "value": 18 + i / 10},
            {"Month": label, "Indicator": "NPL", "value": 14 - i / 10},
            {"Month": label, "Indicator": "ROA", "value": 4 + i / 100},
        ])
    return pd.DataFrame(rows).to_csv(index=False).encode("utf-8")


def test_build_fsi_query_selects_all_months_and_indicators():
    query = bog.build_bog_fsi_query(fsi_metadata())
    selections = {item["code"]: item["selection"] for item in query["query"]}
    assert selections["Month"] == {"filter": "all", "values": ["*"]}
    assert selections["Indicator"] == {"filter": "all", "values": ["*"]}
    assert query["response"]["format"] == "csv"


def test_build_fsi_query_rejects_unidentified_indicator_dimension():
    metadata = fsi_metadata()
    metadata["variables"][1]["valueTexts"] = ["CAR", "NPL", "ROA"]
    with pytest.raises(ValueError, match="indicator dimension"):
        bog.build_bog_fsi_query(metadata)


def test_parse_fsi_csv_returns_long_monthly_data():
    result = bog._parse_bog_fsi_csv(fsi_csv())
    assert list(result.columns) == ["Month", "Indicator Code", "Indicator", "Value"]
    assert len(result) == 36
    assert result["Month"].nunique() == 12
    assert result["Indicator"].nunique() == 3
    assert set(result["Indicator Code"]) == {"CAR", "NPL", "ROA"}
    assert result.iloc[0]["Month"] == "2024M01"
    assert result.iloc[0]["Indicator"] in {"Capital Adequacy Ratio", "Non-Performing Loans", "Return on Assets - Before Tax"}


def test_parse_fsi_csv_rejects_short_data():
    with pytest.raises(ValueError, match="fewer than twelve"):
        bog._parse_bog_fsi_csv(fsi_csv(months=6))


def test_update_fsi_writes_separate_file_and_keeps_existing_files(tmp_path, monkeypatch):
    original = tmp_path / "data_first.csv"
    original.write_text("keep,this\n1,2\n", encoding="utf-8")
    original_bytes = original.read_bytes()
    frame = bog._parse_bog_fsi_csv(fsi_csv())
    monkeypatch.setattr(bog, "fetch_bog_financial_soundness", lambda **kwargs: frame)

    result = bog.update_bog_financial_soundness(raw_data_path=str(tmp_path))
    saved = pd.read_csv(tmp_path / "bog_financial_soundness.csv")

    assert result["latest_month"] == "2024M12"
    assert len(saved) == 36
    assert original.read_bytes() == original_bytes


def test_update_fsi_rejects_stale_data_without_replacing_file(tmp_path, monkeypatch):
    destination = tmp_path / "bog_financial_soundness.csv"
    existing = pd.DataFrame({
        "Month": ["2025M01"],
        "Indicator": ["Capital adequacy ratio"],
        "Value": [20],
    })
    existing.to_csv(destination, index=False)
    original = destination.read_bytes()
    incoming = bog._parse_bog_fsi_csv(fsi_csv())
    monkeypatch.setattr(bog, "fetch_bog_financial_soundness", lambda **kwargs: incoming)

    with pytest.raises(ValueError, match="stale"):
        bog.update_bog_financial_soundness(raw_data_path=str(tmp_path))
    assert destination.read_bytes() == original


def test_fetch_fsi_reads_metadata_then_posts_query(monkeypatch):
    import json

    calls = []
    metadata_payload = json.dumps(fsi_metadata()).encode("utf-8")

    def fake_request(url, data=None, timeout=60):
        calls.append((url, data, timeout))
        return metadata_payload if data is None else fsi_csv()

    monkeypatch.setattr(bog, "_request_bytes", fake_request)
    result = bog.fetch_bog_financial_soundness(
        api_url="https://example.test/fin_sound.px", timeout=20
    )
    assert len(calls) == 2
    assert calls[0][1] is None
    assert calls[1][1] is not None
    assert calls[0][2] == 20
    assert result["Month"].nunique() == 12


def test_fetch_fsi_requires_https():
    with pytest.raises(ValueError, match="HTTPS"):
        bog.fetch_bog_financial_soundness(api_url="http://example.test/fin_sound.px")


def test_parse_fsi_csv_rejects_duplicate_month_indicator_rows():
    frame = pd.DataFrame({
        "Month": ["2024M01"] * 3 + ["2024M02"] * 3,
        "Indicator": [
            "Capital adequacy ratio", "Capital adequacy ratio",
            "Non Performing Loans", "Non Performing Loans",
            "Return on Assets", "Return on Assets",
        ],
        "value": [18, 18, 14, 14, 4, 4],
    })
    payload = frame.to_csv(index=False).encode("utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        bog._parse_bog_fsi_csv(payload)


def test_parse_fsi_csv_rejects_missing_core_indicator():
    frame = pd.DataFrame({
        "Month": ["2024M{:02d}".format(month) for month in range(1, 13)],
        "Indicator": ["CAR"] * 12,
        "value": [18] * 12,
    })
    payload = frame.to_csv(index=False).encode("utf-8")
    with pytest.raises(ValueError, match="missing required core indicators"):
        bog._parse_bog_fsi_csv(payload)
