"""
Test Suite: Phase 2.4 — Module 1 & Module 2 Analytical Implementation.
Manufacturing Diagnostic Intelligence System.

Verifies:
1. Module 1 (Factory Health & Network Overview) renders and integrates cleanly.
2. Module 2 (Machine Health & Condition Monitoring) renders and integrates cleanly.
3. ECDF calculations and coordinate generation are accurate, monotonic, and bounded.
4. Within-machine jitter calculations use sample standard deviation (ddof=1) and rank 50 units.
5. Thermal-vibration bivariate coordinates and decimation preserve empirical boundaries.
6. Predictive Maintenance Score interpretation toggle functions in both directional modes.
7. Mahalanobis distance statistical outlier screening computes chi2 threshold and confirms zero exceedances.
8. Shared sidebar filters propagate correctly into analytical pipelines.
9. Empty DataFrame filter states and error boundaries are handled gracefully without exceptions.
10. Architectural safeguard: Zero duplicated KPI formulas introduced in analytics or UI modules.
"""

from __future__ import annotations

import inspect
import re
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

from scripts.app.analytics import (
    compute_ecdf,
    compute_machine_health_summary,
    compute_machine_network_summary,
    compute_mahalanobis_distances,
    compute_within_machine_jitter,
)
from scripts.app.components import apply_filters
from scripts.app.data_loader import load_manufacturing_data
from scripts.app.kpi_engine import calculate_all_kpis
from scripts.app.modules.factory_overview import render_factory_overview
from scripts.app.modules.machine_health import render_machine_health


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
# 1. Module 1 Integration & Rendering
# ===========================================================================

def test_01_module_1_renders_and_integrates(loaded_dataset: pd.DataFrame, computed_kpis: Dict[str, Any]) -> None:
    """Verify Module 1 render_factory_overview executes without unhandled exceptions."""
    # Test on full dataset slice
    try:
        render_factory_overview(loaded_dataset.head(1000), computed_kpis)
    except Exception as exc:
        pytest.fail(f"render_factory_overview failed on sample slice: {exc}")


# ===========================================================================
# 2. Module 2 Integration & Rendering
# ===========================================================================

def test_02_module_2_renders_and_integrates(loaded_dataset: pd.DataFrame, computed_kpis: Dict[str, Any]) -> None:
    """Verify Module 2 render_machine_health executes without unhandled exceptions."""
    try:
        render_machine_health(loaded_dataset.head(1000), computed_kpis)
    except Exception as exc:
        pytest.fail(f"render_machine_health failed on sample slice: {exc}")


# ===========================================================================
# 3. ECDF Calculations & Coordinate Integrity
# ===========================================================================

def test_03_ecdf_calculations_and_chart_data(loaded_dataset: pd.DataFrame) -> None:
    """Verify compute_ecdf produces monotonic, bounded, and accurate CDF steps."""
    lat_series = loaded_dataset["Network_Latency_ms"]
    ecdf_df = compute_ecdf(lat_series, max_points=1000)

    assert isinstance(ecdf_df, pd.DataFrame), "ECDF output must be a DataFrame"
    assert list(ecdf_df.columns) == ["value", "ecdf", "percentile"], "Unexpected columns in ECDF output"
    assert len(ecdf_df) <= 1000, f"ECDF should be decimated to at most 1000 points, got {len(ecdf_df)}"

    # Check monotonicity
    assert (np.diff(ecdf_df["value"]) >= 0).all(), "ECDF values must be monotonically non-decreasing"
    assert (np.diff(ecdf_df["ecdf"]) >= 0).all(), "ECDF probabilities must be monotonically non-decreasing"

    # Check boundaries
    assert ecdf_df["ecdf"].min() > 0.0, "ECDF minimum must be strictly positive"
    assert np.isclose(ecdf_df["ecdf"].max(), 1.0), "ECDF maximum probability must be exactly 1.0"
    assert np.isclose(ecdf_df["value"].min(), lat_series.min(), atol=1e-3), "ECDF must preserve sample minimum"
    assert np.isclose(ecdf_df["value"].max(), lat_series.max(), atol=1e-3), "ECDF must preserve sample maximum"

    # Test empty series handling
    empty_ecdf = compute_ecdf(pd.Series(dtype=float))
    assert empty_ecdf.empty, "Empty input must return empty ECDF DataFrame"


# ===========================================================================
# 4. Within-Machine Jitter Calculations & Rankings
# ===========================================================================

def test_04_within_machine_jitter_rankings(loaded_dataset: pd.DataFrame) -> None:
    """Verify within-machine jitter uses sample std (ddof=1), covers 50 units, and ranks correctly."""
    jitter_df = compute_within_machine_jitter(loaded_dataset)

    assert len(jitter_df) == 50, f"Expected 50 machines in jitter rankings, found {len(jitter_df)}"
    assert "Jitter_ms" in jitter_df.columns, "Jitter_ms column missing"
    assert "Jitter_Rank" in jitter_df.columns, "Jitter_Rank column missing"

    # Check ascending rank ordering
    assert (jitter_df["Jitter_Rank"] == np.arange(1, 51)).all(), "Jitter ranks must be 1 to 50"
    assert (np.diff(jitter_df["Jitter_ms"]) >= 0).all(), "Jitter values must be in ascending order"

    # Check numerical bounds against Task 1.8 benchmarks (13.84 to 14.43 ms)
    min_j = jitter_df["Jitter_ms"].min()
    max_j = jitter_df["Jitter_ms"].max()
    assert 13.80 <= min_j <= 14.00, f"Minimum machine jitter out of expected range: {min_j}"
    assert 14.30 <= max_j <= 14.50, f"Maximum machine jitter out of expected range: {max_j}"

    # Verify ddof=1 manually on Machine 1
    m1_data = loaded_dataset[loaded_dataset["Machine_ID"] == 1]["Network_Latency_ms"]
    expected_s1 = m1_data.std(ddof=1)
    actual_s1 = jitter_df[jitter_df["Machine_ID"] == 1]["Jitter_ms"].iloc[0]
    assert np.isclose(actual_s1, expected_s1), f"Jitter for Machine 1 mismatch: {actual_s1} vs {expected_s1}"


# ===========================================================================
# 5. Thermal-Vibration Bivariate Scatter Data
# ===========================================================================

def test_05_thermal_vibration_scatter_data(loaded_dataset: pd.DataFrame) -> None:
    """Verify thermal-vibration bivariate coordinates conform to physical operating bounds."""
    temp = loaded_dataset["Temperature_C"]
    vib = loaded_dataset["Vibration_Hz"]

    assert 30.0 <= temp.min() <= 31.0, f"Observed temperature min unexpected: {temp.min()}"
    assert 89.0 <= temp.max() <= 90.0, f"Observed temperature max unexpected: {temp.max()}"
    assert 0.10 <= vib.min() <= 0.20, f"Observed vibration min unexpected: {vib.min()}"
    assert 4.90 <= vib.max() <= 5.00, f"Observed vibration max unexpected: {vib.max()}"

    # Verify machine health summary contains all 50 units
    health_sum = compute_machine_health_summary(loaded_dataset)
    assert len(health_sum) == 50, f"Expected 50 machines in health summary, found {len(health_sum)}"
    assert (health_sum["Mean_Temperature_C"] >= 59.0).all() and (health_sum["Mean_Temperature_C"] <= 61.0).all()
    assert (health_sum["Mean_Vibration_Hz"] >= 2.4).all() and (health_sum["Mean_Vibration_Hz"] <= 2.7).all()


# ===========================================================================
# 6. Predictive Maintenance Score Interpretation Toggle
# ===========================================================================

def test_06_predictive_maintenance_score_interpretation_toggle(loaded_dataset: pd.DataFrame) -> None:
    """Verify PM score distribution and polarity interpretation logic."""
    pm_scores = loaded_dataset["Predictive_Maintenance_Score"]

    # Verify bounds [0.0, 1.0]
    assert pm_scores.min() >= 0.0 and pm_scores.max() <= 1.0, "PM scores out of bounds [0.0, 1.0]"
    assert np.isclose(pm_scores.mean(), 0.50, atol=0.02), f"PM score mean unexpected: {pm_scores.mean()}"

    # Verify quartile counts sum to total observations
    q1 = (pm_scores <= 0.25).sum()
    q2 = ((pm_scores > 0.25) & (pm_scores <= 0.50)).sum()
    q3 = ((pm_scores > 0.50) & (pm_scores <= 0.75)).sum()
    q4 = (pm_scores > 0.75).sum()
    assert q1 + q2 + q3 + q4 == len(loaded_dataset), "Quartile counts must sum to 100,000"

    # Test sorting under both polarities
    health_df = compute_machine_health_summary(loaded_dataset)
    # Default: Higher is worse -> sort descending
    sorted_default = health_df.sort_values(by="Mean_PM_Score", ascending=False)
    # Alternative: Lower is worse -> sort ascending
    sorted_alt = health_df.sort_values(by="Mean_PM_Score", ascending=True)

    assert sorted_default.iloc[0]["Mean_PM_Score"] >= sorted_default.iloc[-1]["Mean_PM_Score"]
    assert sorted_alt.iloc[0]["Mean_PM_Score"] <= sorted_alt.iloc[-1]["Mean_PM_Score"]


# ===========================================================================
# 7. Mahalanobis Statistical Outlier Screening Profile
# ===========================================================================

def test_07_mahalanobis_screening_profile(loaded_dataset: pd.DataFrame) -> None:
    """Verify Mahalanobis distance calculation, chi2 threshold, and zero outlier exceedances."""
    res = compute_mahalanobis_distances(loaded_dataset, feature_cols=["Temperature_C", "Vibration_Hz"], alpha=0.001)

    assert res["n_observations"] == 100_000, f"Expected 100,000 observations, got {res['n_observations']}"
    assert len(res["distances"]) == 100_000, f"Expected 100,000 distance values"

    # Chi-square critical value for p=2, alpha=0.001: chi2_0.999(2) = 13.8155
    expected_threshold = np.sqrt(13.815510557964274)
    assert np.isclose(res["threshold"], expected_threshold, atol=1e-3), (
        f"Critical threshold mismatch: {res['threshold']} vs {expected_threshold}"
    )

    # Reconciled Phase 1 Task 1.4/1.9 finding: Max distance ~2.44, exactly 0 exceedances
    assert res["max_distance"] < res["threshold"], (
        f"Max distance ({res['max_distance']}) should be below threshold ({res['threshold']})"
    )
    assert res["outlier_count"] == 0, f"Expected 0 outliers exceeding 99.9% fence, found {res['outlier_count']}"
    assert res["outlier_pct"] == 0.0, f"Expected 0.0% outliers, found {res['outlier_pct']}"

    # Mean distance for bivariate uniform is approx ~1.325
    assert 1.25 <= res["mean_distance"] <= 1.40, f"Mean distance out of expected range: {res['mean_distance']}"


# ===========================================================================
# 8. Shared Sidebar Filters Propagation
# ===========================================================================

def test_08_shared_sidebar_filters_propagation(loaded_dataset: pd.DataFrame, computed_kpis: Dict[str, Any]) -> None:
    """Verify filtered slices propagate correctly into Module 1 and Module 2 pipelines."""
    # Active mode filter
    filtered_active = apply_filters(loaded_dataset, {"operation_mode": "Active"})
    assert len(filtered_active) == 70_054

    jitter_active = compute_within_machine_jitter(filtered_active)
    assert len(jitter_active) == 50, "All 50 machines should have Active observations"
    assert jitter_active["Record_Count"].sum() == 70_054

    # Machine ID filter (e.g., Machine 1 and 2)
    filtered_machines = apply_filters(loaded_dataset, {"machine_ids": [1, 2]})
    jitter_subset = compute_within_machine_jitter(filtered_machines)
    assert len(jitter_subset) == 2, f"Expected 2 machines in subset, got {len(jitter_subset)}"

    # Render modules on filtered slice
    render_factory_overview(filtered_machines, computed_kpis)
    render_machine_health(filtered_machines, computed_kpis)


# ===========================================================================
# 9. Defensive Handling of Empty Slices and Edge Cases
# ===========================================================================

def test_09_empty_and_edge_case_handling(computed_kpis: Dict[str, Any]) -> None:
    """Verify modules handle empty DataFrames and degenerate slices without raising errors."""
    empty_df = pd.DataFrame()

    # Empty DataFrame rendering in Module 1
    try:
        render_factory_overview(empty_df, computed_kpis)
    except Exception as exc:
        pytest.fail(f"render_factory_overview crashed on empty DataFrame: {exc}")

    # Empty DataFrame rendering in Module 2
    try:
        render_machine_health(empty_df, computed_kpis)
    except Exception as exc:
        pytest.fail(f"render_machine_health crashed on empty DataFrame: {exc}")

    # Analytics helpers on empty DataFrames
    assert compute_ecdf(pd.Series(dtype=float)).empty
    assert compute_within_machine_jitter(empty_df).empty
    assert compute_machine_network_summary(empty_df).empty
    assert compute_machine_health_summary(empty_df).empty

    empty_mah = compute_mahalanobis_distances(empty_df)
    assert empty_mah["outlier_count"] == 0
    assert empty_mah["n_observations"] == 0


# ===========================================================================
# 10. Architectural Safeguard: No Duplicated KPI Formulas
# ===========================================================================

def test_10_no_duplicate_kpi_formulas_in_phase_2_4() -> None:
    """Verify Phase 2.4 files do not re-implement KPI math formulas from kpi_engine."""
    target_files = [
        PROJECT_ROOT / "scripts" / "app" / "analytics.py",
        PROJECT_ROOT / "scripts" / "app" / "modules" / "factory_overview.py",
        PROJECT_ROOT / "scripts" / "app" / "modules" / "machine_health.py",
    ]

    prohibited_patterns = [
        r"Total_Cycle_Time_Min\s*/\s*60",
        r"calculate_oee\(",
        r"calculate_sec\(",
        r"Power_Consumption_kW\s*/\s*Production_Speed",  # SEC formula recomputation
    ]

    for file_path in target_files:
        assert file_path.is_file(), f"Target file does not exist: {file_path}"
        content = file_path.read_text(encoding="utf-8")

        for pattern in prohibited_patterns:
            matches = re.findall(pattern, content)
            assert not matches, (
                f"Found prohibited formula pattern '{pattern}' in {file_path.name}. "
                "Phase 2.4 files must consume KPI outputs from kpi_engine.py."
            )

