"""Structural checks for reproducible research notebooks."""

import ast
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIAGNOSTICS_NOTEBOOK = ROOT / "notebooks" / "03_time_series_diagnostics.ipynb"


def _load_diagnostics_notebook():
    """Load the diagnostics notebook and validate its basic nbformat structure."""
    with DIAGNOSTICS_NOTEBOOK.open(encoding="utf-8") as notebook_file:
        notebook = json.load(notebook_file)

    assert notebook["nbformat"] == 4
    assert isinstance(notebook["cells"], list)
    return notebook


def test_time_series_diagnostics_notebook_code_cells_parse():
    """Every Python code cell should be syntactically valid Python."""
    notebook = _load_diagnostics_notebook()

    code_cells = [
        (index, cell)
        for index, cell in enumerate(notebook["cells"])
        if cell.get("cell_type") == "code"
    ]
    assert code_cells, "The diagnostics notebook contains no Python code cells."

    for index, cell in code_cells:
        source = cell.get("source", "")
        if isinstance(source, list):
            source = "".join(source)
        ast.parse(source, filename=f"03_time_series_diagnostics.ipynb cell {index}")


def test_time_series_diagnostics_notebook_contains_required_checks():
    """The notebook should retain the agreed diagnostics and a disabled VAR gate."""
    notebook = _load_diagnostics_notebook()
    all_source = "\n".join(
        "".join(cell.get("source", []))
        if isinstance(cell.get("source", ""), list)
        else cell.get("source", "")
        for cell in notebook["cells"]
    )

    # The notebook delegates ADF, PP and KPSS to the shared package engine.
    # Keep implementation-specific test classes out of notebook orchestration.
    unit_root_module = ROOT / "src" / "ghana_banking" / "econometrics" / "unit_root.py"
    unit_root_source = unit_root_module.read_text(encoding="utf-8")

    assert "run_unit_root_suite" in all_source
    assert "PhillipsPerron" in unit_root_source
    assert "KPSS" in unit_root_source
    break_module = ROOT / "src" / "ghana_banking" / "econometrics" / "structural_breaks.py"
    break_source = break_module.read_text(encoding="utf-8")
    assert "run_zivot_andrews_test" in all_source
    assert "zivot_andrews" in break_source
    assert "break_date" in break_source
    assert "monthly_unit_root_tests.csv" in all_source
    assert "quarterly_gdp_unit_root_tests.csv" in all_source
    assert "RUN_CANDIDATE_VAR_LAG_SELECTION = False" in all_source
    assert "GDP_Real" in all_source
    assert "RUN_PARAMETER_STABILITY = False" in all_source
    assert "assess_model_eligibility" in all_source
    assert "run_ols_stability_diagnostics" in all_source
    assert "RUN_JOHANSEN_TEST = False" in all_source
    assert "run_johansen_cointegration_test" in all_source
    assert "RUN_ARDL_BOUNDS_TEST = False" in all_source
    assert "fit_ardl_bounds_model" in all_source
