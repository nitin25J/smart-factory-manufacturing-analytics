"""
Test Suite: Task 2.3 — Streamlit Dashboard Shell & Navigation Framework.
Manufacturing Diagnostic Intelligence System.

Verifies:
1. App entrypoint exists, imports cleanly, and defines MODULE_REGISTRY with 4 modules.
2. Navigation contains all four approved analytical modules in correct order.
3. Module entrypoints are callable with (df, kpis) signature.
4. Data access engine integration (delegation to scripts/app/data_loader.py, 100k rows).
5. KPI engine integration (delegation to scripts/app/kpi_engine.py, 5 KPI domains).
6. Reusable presentation components behavior (headers, cards, error/empty states).
7. Pure filter logic, parameter boundaries, and empty-state handling.
8. Architectural safeguard: Zero duplicated mathematical KPI formulas in UI layer.
9. Headless execution verification across all 4 modules and subprocess execution.
"""

from __future__ import annotations

import inspect
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

# Ensure project root is available
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import app
from scripts.app.components import (
    apply_filters,
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
# 1. App Entrypoint & Registry Tests
# ===========================================================================

def test_01_app_entrypoint_exists_and_imports() -> None:
    """Verify app.py exists at project root, imports cleanly, and exports required objects."""
    app_file = PROJECT_ROOT / "app.py"
    assert app_file.is_file(), f"app.py not found at project root: {app_file}"

    assert hasattr(app, "MODULE_REGISTRY"), "app.py must define MODULE_REGISTRY"
    assert isinstance(app.MODULE_REGISTRY, dict), "MODULE_REGISTRY must be a dictionary"
    assert len(app.MODULE_REGISTRY) == 4, f"Expected 4 modules in registry, found {len(app.MODULE_REGISTRY)}"

    assert hasattr(app, "main"), "app.py must define main() entrypoint"
    assert callable(app.main), "app.main must be callable"

    assert hasattr(app, "load_application_data"), "app.py must define load_application_data"
    assert hasattr(app, "compute_application_kpis"), "app.py must define compute_application_kpis"


# ===========================================================================
# 2. Navigation & Four Approved Modules
# ===========================================================================

def test_02_navigation_contains_all_four_modules() -> None:
    """Verify MODULE_REGISTRY contains the exact four modules approved in Phase 2.0 Scope Freeze."""
    expected_keys = [
        "factory_overview",
        "machine_health",
        "production_energy",
        "quality_efficiency",
    ]
    actual_keys = list(app.MODULE_REGISTRY.keys())
    assert actual_keys == expected_keys, f"Registry keys mismatch: {actual_keys} vs {expected_keys}"

    expected_names = [
        "Module 1: Factory Health & Network Overview",
        "Module 2: Machine Health & Condition Monitoring",
        "Module 3: Production Throughput & Energy Monitoring",
        "Module 4: Quality Assurance & Efficiency Diagnostics",
    ]

    for idx, (key, meta) in enumerate(app.MODULE_REGISTRY.items(), start=1):
        assert meta["index"] == idx, f"Module {key} has index {meta['index']}, expected {idx}"
        assert meta["name"] == expected_names[idx - 1], f"Module {key} name mismatch: {meta['name']}"
        assert "short_name" in meta, f"Module {key} missing short_name"
        assert "pillar" in meta, f"Module {key} missing pillar"
        assert "render_fn" in meta, f"Module {key} missing render_fn"
        assert callable(meta["render_fn"]), f"Module {key} render_fn must be callable"


# ===========================================================================
# 3. Module Entrypoints Callable & Signature
# ===========================================================================

def test_03_module_entrypoints_callable(loaded_dataset: pd.DataFrame, computed_kpis: Dict[str, Any]) -> None:
    """Verify each module entrypoint has callable (df, kpis) signature and executes cleanly."""
    modules = [
        ("Module 1", render_factory_overview),
        ("Module 2", render_machine_health),
        ("Module 3", render_production_energy),
        ("Module 4", render_quality_efficiency),
    ]

    sample_slice = loaded_dataset.head(500)

    for name, fn in modules:
        sig = inspect.signature(fn)
        params = list(sig.parameters.keys())
        assert len(params) == 2, f"{name} render function must accept 2 parameters, got {params}"
        assert params[0] == "df", f"{name} first parameter must be 'df', got {params[0]}"
        assert params[1] == "kpis", f"{name} second parameter must be 'kpis', got {params[1]}"

        # Execute headless in test mode
        try:
            fn(sample_slice, computed_kpis)
        except Exception as exc:
            pytest.fail(f"{name} render function failed with exception: {exc}")


# ===========================================================================
# 4. Data Access Engine Integration
# ===========================================================================

def test_04_data_access_engine_integration() -> None:
    """Verify app.load_application_data delegates to data_loader and returns 100k rows."""
    df = app.load_application_data()
    assert isinstance(df, pd.DataFrame), "load_application_data must return a pandas DataFrame"
    assert len(df) == 100_000, f"Expected 100,000 rows, got {len(df)}"
    assert len(df.columns) == 15, f"Expected 15 columns (14 raw + parsed datetime), got {len(df.columns)}"
    assert "datetime" in df.columns, "datetime column must be present"
    assert "Machine_ID" in df.columns, "Machine_ID column must be present"
    assert "Operation_Mode" in df.columns, "Operation_Mode column must be present"

    # Verify no duplicate loading logic in app.py source
    app_source = inspect.getsource(app.load_application_data)
    assert "load_manufacturing_data" in app_source, (
        "load_application_data must delegate to load_manufacturing_data"
    )
    assert "pd.read_csv" not in app_source, (
        "app.py must NOT read CSV files directly; must use data_loader.py"
    )


# ===========================================================================
# 5. KPI Engine Integration
# ===========================================================================

def test_05_kpi_engine_integration(loaded_dataset: pd.DataFrame) -> None:
    """Verify app.compute_application_kpis delegates to kpi_engine and returns 5 domains."""
    sample_df = loaded_dataset.head(1000)
    kpis = app.compute_application_kpis(sample_df)
    assert isinstance(kpis, dict), "compute_application_kpis must return a dictionary"

    expected_domains = [
        "machine_health",
        "operational_throughput",
        "product_quality",
        "telemetry_reliability",
        "energy_efficiency",
    ]
    for domain in expected_domains:
        assert domain in kpis, f"Missing KPI domain: {domain}"
        domain_data = kpis[domain]
        assert isinstance(domain_data, dict), f"KPI domain {domain} must be a dict"
        assert "domain" in domain_data, f"KPI domain {domain} missing domain description"
        assert "status" in domain_data, f"KPI domain {domain} missing status"

    # Verify delegation in app.py source
    app_source = inspect.getsource(app.compute_application_kpis)
    assert "calculate_all_kpis" in app_source, (
        "compute_application_kpis must delegate to calculate_all_kpis"
    )


# ===========================================================================
# 6. Reusable Presentation Components Behavior
# ===========================================================================

def test_06_reusable_components_behavior(loaded_dataset: pd.DataFrame) -> None:
    """Verify reusable presentation components execute cleanly without side effects."""
    # Test render_section_header
    render_section_header("Test Title", "Test Description")

    # Test render_kpi_card with various value formats
    render_kpi_card(label="Test Metric 1", value=98.5, unit="%", delta=0.5, subtext="Target: 95%")
    render_kpi_card(label="Test Metric 2", value=1250, unit="u/hr")
    render_kpi_card(label="Test Metric 3", value="OPTIMAL", unit="", subtext="Normal state")

    # Test render_error_state
    test_exc = ValueError("Test exception message")
    render_error_state("Test Error Title", "Test error user guidance", exception=test_exc)

    # Test render_empty_state
    render_empty_state(
        title="No Records Found",
        message="Filter returned 0 records.",
        suggestion="Clear filters to restore data.",
    )

    # Test render_filter_sidebar does not mutate input df
    initial_shape = loaded_dataset.shape
    filters = render_filter_sidebar(loaded_dataset.head(500))
    assert isinstance(filters, dict), "render_filter_sidebar must return a dict"
    assert loaded_dataset.shape == initial_shape, "render_filter_sidebar mutated input DataFrame"


# ===========================================================================
# 7. Pure Filter Logic & Empty-State Handling
# ===========================================================================

def test_07_filter_logic_and_empty_state_handling(loaded_dataset: pd.DataFrame) -> None:
    """Verify apply_filters correctly filters by mode, machine, date, and handles empty slices."""
    initial_len = len(loaded_dataset)

    # 1. No filters (pass-through)
    f_empty: Dict[str, Any] = {}
    res_empty = apply_filters(loaded_dataset, f_empty)
    assert len(res_empty) == initial_len, "Empty filters dict must return all rows"

    # 2. Filter by Operation_Mode ('Active', 'Idle', 'Maintenance')
    f_active = {"operation_mode": "Active"}
    res_active = apply_filters(loaded_dataset, f_active)
    assert len(res_active) > 0, "Active filter should have results"
    assert (res_active["Operation_Mode"] == "Active").all(), "All rows must be Active"

    f_idle = {"operation_mode": "Idle"}
    res_idle = apply_filters(loaded_dataset, f_idle)
    assert len(res_idle) > 0, "Idle filter should have results"
    assert (res_idle["Operation_Mode"] == "Idle").all(), "All rows must be Idle"

    f_maint = {"operation_mode": "Maintenance"}
    res_maint = apply_filters(loaded_dataset, f_maint)
    assert len(res_maint) > 0, "Maintenance filter should have results"
    assert (res_maint["Operation_Mode"] == "Maintenance").all(), "All rows must be Maintenance"

    assert len(res_active) + len(res_idle) + len(res_maint) == initial_len, (
        f"Active ({len(res_active)}) + Idle ({len(res_idle)}) + Maintenance ({len(res_maint)}) "
        f"must equal total rows ({initial_len})"
    )

    # 3. Filter by Machine_IDs
    f_mach = {"machine_ids": [1, 2]}
    res_mach = apply_filters(loaded_dataset, f_mach)
    assert len(res_mach) > 0
    assert set(res_mach["Machine_ID"].unique()).issubset({1, 2})

    # 4. Filter by Date Range
    min_date = loaded_dataset["datetime"].dt.date.min()
    max_date = loaded_dataset["datetime"].dt.date.max()

    mid_date = min_date + (max_date - min_date) // 2
    f_date = {"date_range": (min_date, mid_date)}
    res_date = apply_filters(loaded_dataset, f_date)
    assert len(res_date) > 0
    assert (res_date["datetime"].dt.date <= mid_date).all()
    assert (res_date["datetime"].dt.date >= min_date).all()

    # 5. Combined Filters
    f_comb = {
        "operation_mode": "Active",
        "machine_ids": [1],
        "date_range": (min_date, mid_date),
    }
    res_comb = apply_filters(loaded_dataset, f_comb)
    assert (res_comb["Operation_Mode"] == "Active").all()
    assert (res_comb["Machine_ID"] == 1).all()
    assert (res_comb["datetime"].dt.date <= mid_date).all()

    # 6. Empty Slices
    # Explicitly empty mode selection
    f_zero_modes = {"selected_modes": []}
    res_zero_modes = apply_filters(loaded_dataset, f_zero_modes)
    assert len(res_zero_modes) == 0, "Empty modes list must return empty DataFrame"

    # Explicitly empty machine selection
    f_zero_mach = {"selected_machines": []}
    res_zero_mach = apply_filters(loaded_dataset, f_zero_mach)
    assert len(res_zero_mach) == 0, "Empty machine list must return empty DataFrame"

    # Non-existent machine filter
    f_none = {"machine_ids": [9999]}
    res_none = apply_filters(loaded_dataset, f_none)
    assert len(res_none) == 0, "Non-existent machine filter must return empty DataFrame"
    assert isinstance(res_none, pd.DataFrame), "Result must still be a DataFrame"

    # 7. Immutability check: loaded_dataset must be unmodified
    assert len(loaded_dataset) == initial_len, "apply_filters must NOT mutate original dataset"


# ===========================================================================
# 8. Architectural Safeguard: No Duplicated KPI Formulas in UI Layer
# ===========================================================================

def test_08_no_duplicate_kpi_formulas_in_app() -> None:
    """Verify UI files do not re-implement mathematical KPI formulas from kpi_engine."""
    target_files = [
        PROJECT_ROOT / "app.py",
        PROJECT_ROOT / "scripts" / "app" / "components.py",
        PROJECT_ROOT / "scripts" / "app" / "modules" / "factory_overview.py",
        PROJECT_ROOT / "scripts" / "app" / "modules" / "machine_health.py",
        PROJECT_ROOT / "scripts" / "app" / "modules" / "production_energy.py",
        PROJECT_ROOT / "scripts" / "app" / "modules" / "quality_efficiency.py",
    ]

    # Prohibited patterns that would indicate re-implementing KPI math rather than using kpi_engine
    # Example: explicit formula recalculations of complex KPIs in UI modules
    prohibited_patterns = [
        r"Total_Cycle_Time_Min\s*/\s*60",  # Cycle time hour conversion math
        r"100\s*-\s*df\[['\"]Quality_Control_Defect_Rate_%\['\"]\]",  # Direct complement recalculation
        r"calculate_oee\(",  # Redefining an OEE calculation function
        r"calculate_qos\(",  # Redefining a QoS calculation function
        r"calculate_sec\(",  # Redefining SEC calculation function
    ]

    for file_path in target_files:
        assert file_path.is_file(), f"Target file does not exist: {file_path}"
        content = file_path.read_text(encoding="utf-8")

        for pattern in prohibited_patterns:
            matches = re.findall(pattern, content)
            assert not matches, (
                f"Found prohibited formula pattern '{pattern}' in {file_path.name}. "
                "UI modules must consume pre-calculated KPI metrics from kpi_engine."
            )


# ===========================================================================
# 9. Headless Execution & Navigation Verification
# ===========================================================================

def test_09_headless_execution_and_navigation() -> None:
    """Verify app.main() executes cleanly across all 4 module choices and via subprocess."""
    # Test app.main() directly in Python runtime for each module
    module_names = [meta["name"] for meta in app.MODULE_REGISTRY.values()]

    for mod_name in module_names:
        with patch("streamlit.sidebar.radio", return_value=mod_name):
            try:
                app.main()
            except Exception as exc:
                pytest.fail(f"app.main() crashed when selecting '{mod_name}': {exc}")

    # Test app.main() handling empty filtered state gracefully
    with patch("scripts.app.components.apply_filters", return_value=pd.DataFrame()):
        try:
            app.main()
        except Exception as exc:
            pytest.fail(f"app.main() crashed on empty filtered DataFrame: {exc}")

    # Subprocess execution test: python app.py bare run
    res = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "app.py")],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(PROJECT_ROOT),
    )
    assert res.returncode == 0, f"Bare python app.py execution failed with exit code {res.returncode}:\n{res.stderr}"
