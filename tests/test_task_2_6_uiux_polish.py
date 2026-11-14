"""
Test Suite: Phase 2.6 — UI/UX Polish, Streamlit Modernization & End-to-End System Verification.
Manufacturing Diagnostic Intelligence System.

Verifies:
1. All four diagnostic modules render and integrate cleanly without unhandled exceptions.
2. 100% title parity between app.MODULE_REGISTRY navigation and module page headings.
3. Standardized KPI card metric formatting (large integers formatted with comma, e.g. 100,000, clean floats).
4. Reusable CSV export component (render_download_button) serializes clean data without DataFrame index.
5. Standardized decimation controls across Modules 2, 3, and 4 (options [1000, 2500, 5000, 10000, 'All Records'], default 5000).
6. Complete elimination of deprecated use_container_width=True in favor of width="stretch".
7. Empty-state defensive resilience across all four modules.
8. Filter propagation through global sidebar filters into all four module views.
9. Architectural safeguard: No duplicate KPI calculations in UI components.
10. Application entry point headless execution across all modules.
"""

from __future__ import annotations

import inspect
import io
import re
import sys
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

# Ensure project root is available in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import app
from scripts.app.components import (
    apply_filters,
    render_download_button,
    render_empty_state,
    render_error_state,
    render_filter_sidebar,
    render_kpi_card,
    render_section_header,
)
from scripts.app.data_loader import load_manufacturing_data
from scripts.app.kpi_engine import calculate_all_kpis
from scripts.app.modules.factory_overview import render_factory_overview
from scripts.app.modules.machine_health import render_machine_health
from scripts.app.modules.production_energy import render_production_energy
from scripts.app.modules.quality_efficiency import render_quality_efficiency


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture(scope="session")
def loaded_dataset() -> pd.DataFrame:
    """Load the validated 100k manufacturing dataset for testing."""
    return load_manufacturing_data(validate=True, add_parsed_datetime=True)


@pytest.fixture(scope="session")
def computed_kpis(loaded_dataset: pd.DataFrame) -> Dict[str, Any]:
    """Compute baseline KPI results for testing."""
    return calculate_all_kpis(loaded_dataset)


# ===========================================================================
# 1. All Four Diagnostic Modules Render and Integrate
# ===========================================================================

def test_01_all_four_modules_render_and_integrate(loaded_dataset: pd.DataFrame, computed_kpis: Dict[str, Any]) -> None:
    """Verify that all four module entry points execute without unhandled exceptions."""
    sample_slice = loaded_dataset.head(1000)

    modules = [
        ("Module 1 (Factory Overview)", render_factory_overview),
        ("Module 2 (Machine Health)", render_machine_health),
        ("Module 3 (Production & Energy)", render_production_energy),
        ("Module 4 (Quality & Efficiency)", render_quality_efficiency),
    ]

    for name, render_fn in modules:
        try:
            render_fn(sample_slice, computed_kpis)
        except Exception as exc:
            pytest.fail(f"{name} failed during rendering: {exc}")


# ===========================================================================
# 2. Module Title Parity Across Registry and Headers
# ===========================================================================

def test_02_module_title_parity_across_registry_and_headers() -> None:
    """Verify 100% exact title parity between app.MODULE_REGISTRY and render_section_header in Modules 1-4."""
    module_files = {
        "factory_overview": PROJECT_ROOT / "scripts" / "app" / "modules" / "factory_overview.py",
        "machine_health": PROJECT_ROOT / "scripts" / "app" / "modules" / "machine_health.py",
        "production_energy": PROJECT_ROOT / "scripts" / "app" / "modules" / "production_energy.py",
        "quality_efficiency": PROJECT_ROOT / "scripts" / "app" / "modules" / "quality_efficiency.py",
    }

    for mod_key, file_path in module_files.items():
        assert mod_key in app.MODULE_REGISTRY, f"Module key '{mod_key}' missing in MODULE_REGISTRY"
        registry_title = app.MODULE_REGISTRY[mod_key]["name"]

        # Parse source code of module file for render_section_header call
        content = file_path.read_text(encoding="utf-8")
        match = re.search(r'render_section_header\s*\(\s*title=["\']([^"\']+)["\']', content)
        assert match is not None, f"Could not find render_section_header title in {file_path.name}"
        header_title = match.group(1)

        assert registry_title == header_title, (
            f"Title mismatch for {mod_key}: "
            f"MODULE_REGISTRY has '{registry_title}' but header has '{header_title}'"
        )


# ===========================================================================
# 3. Standardized KPI Card Metric Formatting
# ===========================================================================

def test_03_kpi_card_large_number_and_float_formatting() -> None:
    """Verify render_kpi_card correctly formats large integers (with commas) and floats without truncation."""
    with patch("streamlit.metric") as mock_metric:
        # Large integer (fleet count: 100,000)
        render_kpi_card("Fleet Count", 100000, unit="records")
        mock_metric.assert_called_with(
            label="Fleet Count",
            value="100,000 records",
            delta=None,
            help=None,
        )

        # Numpy integer (np.int64)
        render_kpi_card("Numpy Fleet Count", np.int64(100000))
        mock_metric.assert_called_with(
            label="Numpy Fleet Count",
            value="100,000",
            delta=None,
            help=None,
        )

        # Floating point >= 1000
        render_kpi_card("Total Throughput", 1250.758, unit="u/hr")
        mock_metric.assert_called_with(
            label="Total Throughput",
            value="1,250.76 u/hr",
            delta=None,
            help=None,
        )

        # Small floating point (SEC in kWh/unit)
        render_kpi_card("SEC Baseline", 0.026389, unit="kWh/unit")
        mock_metric.assert_called_with(
            label="SEC Baseline",
            value="0.026389 kWh/unit",
            delta=None,
            help=None,
        )

        # Floating point >= 1
        render_kpi_card("Mean Power", 5.7423, unit="kW")
        mock_metric.assert_called_with(
            label="Mean Power",
            value="5.7423 kW",
            delta=None,
            help=None,
        )


# ===========================================================================
# 4. Reusable CSV Export Component (render_download_button)
# ===========================================================================

def test_04_csv_export_component_and_serialization() -> None:
    """Verify render_download_button serializes clean data without DataFrame index in UTF-8, stripping accidental index columns."""
    test_df = pd.DataFrame({
        "Unnamed: 0": [0, 1, 2],  # accidental leaked index
        "index": [0, 1, 2],       # auto-generated integer index
        "Machine_ID": [1, 2, 3],
        "Mean_Speed": [275.5, 276.1, 274.8],
        "Status": ["Active", "Idle", "Maintenance"],
    })

    with patch("streamlit.download_button") as mock_dl:
        render_download_button(
            df=test_df,
            filename="test_export.csv",
            label="Download Test CSV",
            key="test_dl_key",
            help_text="Test tooltip",
        )

        mock_dl.assert_called_once()
        call_kwargs = mock_dl.call_args.kwargs

        assert call_kwargs["file_name"] == "test_export.csv"
        assert call_kwargs["mime"] == "text/csv"
        assert call_kwargs["label"] == "Download Test CSV"
        assert call_kwargs["key"] == "test_dl_key"
        assert call_kwargs["help"] == "Test tooltip"

        # Verify CSV payload content
        csv_bytes = call_kwargs["data"]
        assert isinstance(csv_bytes, bytes)
        csv_text = csv_bytes.decode("utf-8")

        # Parse CSV back to DataFrame to confirm integrity and absence of index column
        parsed_df = pd.read_csv(io.StringIO(csv_text))
        assert list(parsed_df.columns) == ["Machine_ID", "Mean_Speed", "Status"]
        assert len(parsed_df) == 3
        assert parsed_df.iloc[0]["Machine_ID"] == 1
        assert "Unnamed: 0" not in parsed_df.columns
        assert "index" not in parsed_df.columns

    # Verify empty DataFrame safely returns without rendering download button
    with patch("streamlit.download_button") as mock_dl_empty:
        render_download_button(df=pd.DataFrame(), filename="empty.csv")
        mock_dl_empty.assert_not_called()


# ===========================================================================
# 5. Standardized Decimation Controls Across Modules 2, 3, and 4
# ===========================================================================

def test_05_standardized_decimation_controls_and_defaults() -> None:
    """Verify decimation options are [1000, 2500, 5000, 10000, 'All Records'] and default to 5000."""
    expected_options = [1000, 2500, 5000, 10000, "All Records"]

    # Module 2 (machine_health.py)
    mod2_content = (PROJECT_ROOT / "scripts" / "app" / "modules" / "machine_health.py").read_text(encoding="utf-8")
    assert "options=[1000, 2500, 5000, 10000, \"All Records\"]" in mod2_content
    assert "value=5000 if n_total >= 5000 else \"All Records\"" in mod2_content

    # Module 3 (production_energy.py)
    mod3_content = (PROJECT_ROOT / "scripts" / "app" / "modules" / "production_energy.py").read_text(encoding="utf-8")
    assert "options=[1000, 2500, 5000, 10000, \"All Records\"]" in mod3_content
    assert "index=2" in mod3_content  # index 2 corresponds to 5000 in expected_options

    # Module 4 (quality_efficiency.py)
    mod4_content = (PROJECT_ROOT / "scripts" / "app" / "modules" / "quality_efficiency.py").read_text(encoding="utf-8")
    assert "options=[1000, 2500, 5000, 10000, \"All Records\"]" in mod4_content
    assert "index=2" in mod4_content  # index 2 corresponds to 5000 in expected_options


# ===========================================================================
# 6. Elimination of Deprecated use_container_width
# ===========================================================================

def test_06_zero_deprecated_use_container_width_and_all_stretch_width() -> None:
    """Verify zero occurrences of deprecated use_container_width across all modules and scripts."""
    scripts_to_check = [
        PROJECT_ROOT / "app.py",
        PROJECT_ROOT / "scripts" / "app" / "components.py",
        PROJECT_ROOT / "scripts" / "app" / "modules" / "factory_overview.py",
        PROJECT_ROOT / "scripts" / "app" / "modules" / "machine_health.py",
        PROJECT_ROOT / "scripts" / "app" / "modules" / "production_energy.py",
        PROJECT_ROOT / "scripts" / "app" / "modules" / "quality_efficiency.py",
    ]

    for script_path in scripts_to_check:
        content = script_path.read_text(encoding="utf-8")
        assert "use_container_width" not in content, (
            f"Found deprecated 'use_container_width' in {script_path.name}. "
            "Must be replaced with width='stretch'."
        )


# ===========================================================================
# 7. Empty State Resilience Across All Four Modules
# ===========================================================================

def test_07_empty_state_resilience_across_all_modules() -> None:
    """Verify all four modules handle empty DataFrames without unhandled exceptions."""
    empty_df = pd.DataFrame()
    empty_kpis: Dict[str, Any] = {
        "kpi_1_machine_health": {},
        "kpi_2_production_performance": {},
        "kpi_3_quality_assurance": {},
        "kpi_4_network_qos": {},
        "kpi_5_energy_efficiency": {},
    }

    modules = [
        ("Module 1", render_factory_overview),
        ("Module 2", render_machine_health),
        ("Module 3", render_production_energy),
        ("Module 4", render_quality_efficiency),
    ]

    for name, render_fn in modules:
        try:
            render_fn(empty_df, empty_kpis)
        except Exception as exc:
            pytest.fail(f"{name} crashed on empty DataFrame: {exc}")


# ===========================================================================
# 8. Filter Propagation Through Global Sidebar
# ===========================================================================

def test_08_filter_propagation_and_module_execution(loaded_dataset: pd.DataFrame, computed_kpis: Dict[str, Any]) -> None:
    """Verify global sidebar filter outputs propagate cleanly into all four modules."""
    # Test specific operational mode and subset of machines
    test_filters = {
        "selected_modes": ["Active"],
        "selected_machines": [1, 2, 3],
        "date_range": (
            loaded_dataset["datetime"].dt.date.min(),
            loaded_dataset["datetime"].dt.date.min() + pd.Timedelta(days=7),
        ),
    }

    filtered_df = apply_filters(loaded_dataset, test_filters)
    assert not filtered_df.empty, "Filtered slice should not be empty"
    assert (filtered_df["Operation_Mode"] == "Active").all()
    assert set(filtered_df["Machine_ID"].unique()).issubset({1, 2, 3})

    # Execute all 4 modules with filtered slice
    for render_fn in [
        render_factory_overview,
        render_machine_health,
        render_production_energy,
        render_quality_efficiency,
    ]:
        try:
            render_fn(filtered_df, computed_kpis)
        except Exception as exc:
            pytest.fail(f"Module execution failed on filtered slice: {exc}")


# ===========================================================================
# 9. Architectural Safeguard: No Duplicate KPI Math in UI Components
# ===========================================================================

def test_09_no_duplicate_kpi_formulas_in_components() -> None:
    """Verify components.py does not define raw formulas for KPI calculations."""
    comp_file = PROJECT_ROOT / "scripts" / "app" / "components.py"
    content = comp_file.read_text(encoding="utf-8")

    prohibited_patterns = [
        r"Power_Consumption_kW\s*/\s*Production_Speed",
        r"Total_Packets_Lost\s*/\s*Total_Packets_Sent",
        r"100\s*-\s*Quality_Control_Defect_Rate",
    ]

    for pattern in prohibited_patterns:
        match = re.search(pattern, content)
        assert match is None, f"Prohibited duplicate formula found in components.py: {pattern}"


# ===========================================================================
# 10. Application Entry Point Headless Execution
# ===========================================================================

def test_10_app_main_headless_execution() -> None:
    """Verify app.main() executes cleanly across all 4 module choices in headless runtime."""
    module_names = [meta["name"] for meta in app.MODULE_REGISTRY.values()]
    assert len(module_names) == 4

    for mod_name in module_names:
        with patch("streamlit.sidebar.radio", return_value=mod_name):
            try:
                app.main()
            except Exception as exc:
                pytest.fail(f"app.main() crashed when rendering module '{mod_name}': {exc}")


# ===========================================================================
# 11. All Five Module CSV Exports Match Displayed Tables (No Unnamed Columns)
# ===========================================================================

def test_11_all_five_module_csv_exports_match_displayed_tables(
    loaded_dataset: pd.DataFrame, computed_kpis: Dict[str, Any]
) -> None:
    """
    Verify all five module CSV exports:
    1. No Unnamed: 0 or leaked index columns
    2. No unnamed columns or empty/whitespace headers
    3. Correct column names matching displayed summary tables
    4. Row counts match full and filtered subsets
    5. Clean deterministic UTF-8 encoding
    """
    expected_exports = {
        "module1_machine_qos_summary.csv": [
            "Machine_ID", "Record_Count", "Mean_Latency_ms", "P95_Latency_ms",
            "Jitter_ms", "Mean_Packet_Loss_pct", "P95_Packet_Loss_pct", "Zero_Loss_Count"
        ],
        "module2_machine_health_summary.csv": [
            "Machine_ID", "Record_Count", "Mean_Temperature_C", "Median_Temperature_C",
            "Mean_Vibration_Hz", "Median_Vibration_Hz", "Mean_PM_Score", "Median_PM_Score", "Max_Mahalanobis_D"
        ],
        "module3_fleet_production_energy_summary.csv": [
            "Machine", "Records", "Speed Mean (u/hr)", "Speed Med (u/hr)",
            "Power Mean (kW)", "Power Med (kW)", "SEC Mean (kWh/u)", "Speed Rank", "Power Rank", "SEC Rank"
        ],
        "module4_machine_quality_summary.csv": [
            "Machine", "Observations", "Defect Mean (%)", "Defect Med (%)",
            "Complement (%)", "Error Mean (%)", "Error Med (%)", "Defect Rank", "Error Rank"
        ],
        "module4_mode_efficiency_contingency.csv": [
            "Mode", "Total", "Low Count", "Low (%)", "Med Count", "Med (%)", "High Count", "High (%)"
        ],
    }

    # --- Part A: Full Dataset Test ---
    captured_full: Dict[str, bytes] = {}

    def mock_capture_full(*args: Any, **kwargs: Any) -> None:
        file_name = kwargs.get("file_name")
        data = kwargs.get("data")
        if file_name and data:
            captured_full[file_name] = data

    with patch("streamlit.download_button", side_effect=mock_capture_full):
        render_factory_overview(loaded_dataset, computed_kpis)
        render_machine_health(loaded_dataset, computed_kpis)
        render_production_energy(loaded_dataset, computed_kpis)
        render_quality_efficiency(loaded_dataset, computed_kpis)

    assert len(captured_full) == 5, f"Expected 5 exports, captured {len(captured_full)}: {list(captured_full.keys())}"

    for filename, expected_cols in expected_exports.items():
        assert filename in captured_full, f"Missing export for {filename}"
        csv_bytes = captured_full[filename]
        csv_text = csv_bytes.decode("utf-8")
        parsed_df = pd.read_csv(io.StringIO(csv_text))

        # Check absence of Unnamed or index columns
        assert "Unnamed: 0" not in parsed_df.columns, f"Unnamed: 0 found in {filename}"
        unnamed_cols = [c for c in parsed_df.columns if "unnamed" in str(c).lower() or str(c).strip() == ""]
        assert len(unnamed_cols) == 0, f"Found unnamed columns in {filename}: {unnamed_cols}"
        assert "index" not in parsed_df.columns, f"'index' column found in {filename}"

        # Check exact column names
        assert list(parsed_df.columns) == expected_cols, (
            f"Column mismatch in {filename}.\nExpected: {expected_cols}\nActual: {list(parsed_df.columns)}"
        )

        # Check row counts
        if "contingency" in filename:
            assert len(parsed_df) == 3, f"Expected 3 rows in contingency table, got {len(parsed_df)}"
        else:
            assert len(parsed_df) == 50, f"Expected 50 machine rows in {filename}, got {len(parsed_df)}"

    # --- Part B: Filtered Subset Test (5 machines only) ---
    subset_df = loaded_dataset[loaded_dataset["Machine_ID"].isin([1, 2, 3, 4, 5])].copy()
    captured_subset: Dict[str, bytes] = {}

    def mock_capture_subset(*args: Any, **kwargs: Any) -> None:
        file_name = kwargs.get("file_name")
        data = kwargs.get("data")
        if file_name and data:
            captured_subset[file_name] = data

    with patch("streamlit.download_button", side_effect=mock_capture_subset):
        render_factory_overview(subset_df, computed_kpis)
        render_machine_health(subset_df, computed_kpis)
        render_production_energy(subset_df, computed_kpis)
        render_quality_efficiency(subset_df, computed_kpis)

    for filename in [
        "module1_machine_qos_summary.csv",
        "module2_machine_health_summary.csv",
        "module3_fleet_production_energy_summary.csv",
        "module4_machine_quality_summary.csv",
    ]:
        assert filename in captured_subset, f"Missing filtered export for {filename}"
        parsed_sub = pd.read_csv(io.StringIO(captured_subset[filename].decode("utf-8")))
        assert len(parsed_sub) == 5, f"Expected 5 filtered rows in {filename}, got {len(parsed_sub)}"
        assert "Unnamed: 0" not in parsed_sub.columns


