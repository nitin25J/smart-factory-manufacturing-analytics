"""
Test Suite: Phase 2.5 — Module 3 & Module 4 Analytical Implementation.
Manufacturing Diagnostic Intelligence System.

Verifies:
1. Module 3 (Production Throughput & Energy Performance) renders and integrates cleanly.
2. Module 4 (Quality Assurance & Process Efficiency Diagnostics) renders and integrates cleanly.
3. Production-speed calculations, aggregations, and competitive rankings across all 50 units.
4. Power-consumption statistics, distributions, and mode-stratified allocations.
5. Specific Energy Consumption (SEC in kWh/unit) row-level calculation with strict non-positive speed exclusions.
6. Temporal daily summaries across all 69 calendar dates in chronological order.
7. Finished-good defect rates, process error rates, and the arithmetic complement (94.991194%).
8. Empirical Efficiency_Status contingency allocations across operating modes and machines.
9. Defensive resilience against empty DataFrames, missing columns, division by zero, and degenerate slices.
10. Architectural safeguard: Zero duplicated KPI engine formulas in Phase 2.5 modules.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any, Dict

import numpy as np
import pandas as pd
import pytest

# Ensure project root is available in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.app.analytics import (
    compute_efficiency_contingency,
    compute_mode_stratified_summary,
    compute_production_energy_summary,
    compute_quality_machine_summary,
    compute_temporal_daily_summary,
)
from scripts.app.components import apply_filters
from scripts.app.data_loader import load_manufacturing_data
from scripts.app.kpi_engine import calculate_all_kpis
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
# 1. Module 3 Integration & Rendering
# ===========================================================================

def test_01_module_3_renders_and_integrates(loaded_dataset: pd.DataFrame, computed_kpis: Dict[str, Any]) -> None:
    """Verify Module 3 render_production_energy executes without unhandled exceptions."""
    try:
        render_production_energy(loaded_dataset.head(1000), computed_kpis)
    except Exception as exc:
        pytest.fail(f"render_production_energy failed on sample slice: {exc}")


# ===========================================================================
# 2. Module 4 Integration & Rendering
# ===========================================================================

def test_02_module_4_renders_and_integrates(loaded_dataset: pd.DataFrame, computed_kpis: Dict[str, Any]) -> None:
    """Verify Module 4 render_quality_efficiency executes without unhandled exceptions."""
    try:
        render_quality_efficiency(loaded_dataset.head(1000), computed_kpis)
    except Exception as exc:
        pytest.fail(f"render_quality_efficiency failed on sample slice: {exc}")


# ===========================================================================
# 3. Production Speed Aggregations & Machine Rankings
# ===========================================================================

def test_03_production_speed_aggregations_and_rankings(loaded_dataset: pd.DataFrame) -> None:
    """Verify production-speed machine summary calculates metrics, bounds, and ranks correctly."""
    summary_df = compute_production_energy_summary(loaded_dataset)

    assert len(summary_df) == 50, f"Expected 50 machines in production summary, got {len(summary_df)}"
    assert "Speed_Rank" in summary_df.columns
    assert "Mean_Speed_u_per_hr" in summary_df.columns

    # Ranks must be complete 1 to 50
    assert set(summary_df["Speed_Rank"]) == set(range(1, 51))

    # All machine mean speeds must fall within empirical Task 1.6 bounds [270, 285] u/hr
    assert (summary_df["Mean_Speed_u_per_hr"] >= 270.0).all()
    assert (summary_df["Mean_Speed_u_per_hr"] <= 285.0).all()

    # Grand mean speed must match Task 1.6 baseline ~275.92 u/hr
    overall_mean = loaded_dataset["Production_Speed_units_per_hr"].mean()
    assert np.isclose(overall_mean, 275.9163, atol=1e-2)


# ===========================================================================
# 4. Power Consumption Statistics & Mode Grouping
# ===========================================================================

def test_04_power_consumption_statistics_and_modes(loaded_dataset: pd.DataFrame) -> None:
    """Verify power consumption statistics and mode allocations across Active, Idle, Maintenance."""
    mode_df = compute_mode_stratified_summary(loaded_dataset)

    assert len(mode_df) == 3, f"Expected 3 operation modes, found {len(mode_df)}"
    assert set(mode_df["Operation_Mode"]) == {"Active", "Idle", "Maintenance"}

    # Record counts match Task 1.6 audit
    mode_counts = mode_df.set_index("Operation_Mode")["Record_Count"].to_dict()
    assert mode_counts["Active"] == 70_054
    assert mode_counts["Idle"] == 20_057
    assert mode_counts["Maintenance"] == 9_889

    # Power consumption mean is ~5.75 kW across all modes
    for mode in ["Active", "Idle", "Maintenance"]:
        p_mean = mode_df.loc[mode_df["Operation_Mode"] == mode, "Mean_Power_kW"].iloc[0]
        assert 5.70 <= p_mean <= 5.80, f"Power mean for {mode} out of range: {p_mean}"


# ===========================================================================
# 5. SEC Calculation & Non-Positive Speed Exclusion
# ===========================================================================

def test_05_sec_calculation_and_non_positive_speed_exclusion(loaded_dataset: pd.DataFrame) -> None:
    """Verify row-level SEC evaluation, verified units (kWh/unit), and division-by-zero protection."""
    summary_df = compute_production_energy_summary(loaded_dataset)

    # In raw dataset, all speeds are in [50, 500) > 0
    assert (summary_df["Mean_SEC_kWh_per_u"] > 0.0).all()
    # SEC is bounded between 0.02 and 0.04 kWh/unit on machine averages
    assert (summary_df["Mean_SEC_kWh_per_u"] >= 0.025).all()
    assert (summary_df["Mean_SEC_kWh_per_u"] <= 0.035).all()

    # Synthetic test for non-positive speed exclusion and division-by-zero prevention
    synth_df = pd.DataFrame({
        "Machine_ID": [99, 99, 99, 99],
        "Production_Speed_units_per_hr": [0.0, -10.0, 100.0, 200.0],
        "Power_Consumption_kW": [5.0, 5.0, 5.0, 5.0],
    })
    synth_res = compute_production_energy_summary(synth_df)
    assert len(synth_res) == 1
    # Only records 3 and 4 (speeds 100 and 200) are eligible: SEC = 5/100 (0.05) and 5/200 (0.025), mean = 0.0375
    expected_sec = (0.05 + 0.025) / 2.0
    assert np.isclose(synth_res["Mean_SEC_kWh_per_u"].iloc[0], expected_sec), (
        f"SEC mismatch: {synth_res['Mean_SEC_kWh_per_u'].iloc[0]} vs {expected_sec}"
    )


# ===========================================================================
# 6. Temporal Daily Summaries Across All 69 Calendar Dates
# ===========================================================================

def test_06_temporal_daily_summaries(loaded_dataset: pd.DataFrame) -> None:
    """Verify compute_temporal_daily_summary aggregates all 69 dates in chronological sequence."""
    daily_df = compute_temporal_daily_summary(loaded_dataset)

    assert len(daily_df) == 69, f"Expected 69 calendar dates, got {len(daily_df)}"
    assert daily_df["Record_Count"].sum() == 100_000, "Total daily observations must sum to 100,000"

    # Check date monotonicity
    assert (np.diff(daily_df["parsed_date"]) > np.timedelta64(0, "s")).all(), (
        "Daily timeline must be strictly monotonically increasing in chronological time."
    )

    # First date is 2025-01-01 and last date is 2025-03-10
    assert daily_df["parsed_date"].iloc[0] == pd.Timestamp("2025-01-01")
    assert daily_df["parsed_date"].iloc[-1] == pd.Timestamp("2025-03-10")

    # Day 01-03-2025 has 2,880 records, 10-03-2025 has 640 records (reconciled Task 1.9 check)
    d_0103 = daily_df[daily_df["Date"] == "01-03-2025"]["Record_Count"].iloc[0]
    d_1003 = daily_df[daily_df["Date"] == "10-03-2025"]["Record_Count"].iloc[0]
    assert d_0103 == 2880
    assert d_1003 == 640


# ===========================================================================
# 7. Quality Metrics, Machine Rankings & Arithmetic Complement
# ===========================================================================

def test_07_quality_metrics_and_arithmetic_complement(loaded_dataset: pd.DataFrame) -> None:
    """Verify finished-goods defect rate (~5.01%), error rate (~7.50%), and arithmetic complement."""
    q_summary = compute_quality_machine_summary(loaded_dataset)

    assert len(q_summary) == 50, f"Expected 50 machines in quality summary, got {len(q_summary)}"
    assert "Defect_Rank" in q_summary.columns
    assert "Arithmetic_Complement_pct" in q_summary.columns

    # Arithmetic complement equals strictly 100 - mean defect rate
    for _, row in q_summary.iterrows():
        expected_comp = 100.0 - row["Mean_Defect_Rate_pct"]
        assert np.isclose(row["Arithmetic_Complement_pct"], expected_comp), (
            f"Arithmetic complement mismatch: {row['Arithmetic_Complement_pct']} vs {expected_comp}"
        )

    # Fleet mean defect rate matches Task 1.7 baseline 5.008806%
    overall_defect = loaded_dataset["Quality_Control_Defect_Rate_%"].mean()
    assert np.isclose(overall_defect, 5.008806, atol=1e-4)
    overall_comp = 100.0 - overall_defect
    assert np.isclose(overall_comp, 94.991194, atol=1e-4)

    # Fleet mean error rate matches Task 1.7 baseline 7.504101%
    overall_error = loaded_dataset["Error_Rate_%"].mean()
    assert np.isclose(overall_error, 7.504101, atol=1e-4)


# ===========================================================================
# 8. Efficiency Status Contingency & Tier Allocations
# ===========================================================================

def test_08_efficiency_status_contingency(loaded_dataset: pd.DataFrame) -> None:
    """Verify contingency cross-tabulations across modes and machines."""
    contingency_df = compute_efficiency_contingency(loaded_dataset, row_col="Operation_Mode")

    assert len(contingency_df) == 3
    # Check total sums match empirical counts
    assert contingency_df["Low_Count"].sum() == 77_825
    assert contingency_df["Medium_Count"].sum() == 19_189
    assert contingency_df["High_Count"].sum() == 2_986
    assert contingency_df["Total_Count"].sum() == 100_000

    # Row percentages sum to 100.0%
    row_sum_pct = contingency_df["Low_Pct"] + contingency_df["Medium_Pct"] + contingency_df["High_Pct"]
    assert np.isclose(row_sum_pct, 100.0).all()

    # Machine-level contingency
    mach_ct = compute_efficiency_contingency(loaded_dataset, row_col="Machine_ID")
    assert len(mach_ct) == 50
    assert mach_ct["Total_Count"].sum() == 100_000


# ===========================================================================
# 9. Defensive Handling of Empty Slices and Degenerate Inputs
# ===========================================================================

def test_09_empty_and_degenerate_input_resilience(computed_kpis: Dict[str, Any]) -> None:
    """Verify modules and helper functions handle empty DataFrames gracefully without exceptions."""
    empty_df = pd.DataFrame()

    # Module rendering on empty DataFrames
    try:
        render_production_energy(empty_df, computed_kpis)
    except Exception as exc:
        pytest.fail(f"render_production_energy crashed on empty DataFrame: {exc}")

    try:
        render_quality_efficiency(empty_df, computed_kpis)
    except Exception as exc:
        pytest.fail(f"render_quality_efficiency crashed on empty DataFrame: {exc}")

    # Analytics helpers on empty DataFrames
    assert compute_production_energy_summary(empty_df).empty
    assert compute_temporal_daily_summary(empty_df).empty
    assert compute_mode_stratified_summary(empty_df).empty
    assert compute_quality_machine_summary(empty_df).empty
    assert compute_efficiency_contingency(empty_df).empty


# ===========================================================================
# 10. Architectural Safeguard: No Duplicated KPI Formulas
# ===========================================================================

def test_10_no_duplicate_kpi_formulas_in_phase_2_5() -> None:
    """Verify Phase 2.5 files consume kpi_engine and do not re-implement prohibited formulas."""
    target_files = [
        PROJECT_ROOT / "scripts" / "app" / "analytics.py",
        PROJECT_ROOT / "scripts" / "app" / "modules" / "production_energy.py",
        PROJECT_ROOT / "scripts" / "app" / "modules" / "quality_efficiency.py",
    ]

    prohibited_patterns = [
        r"Total_Cycle_Time_Min\s*/\s*60",
        r"calculate_oee\(",
        r"calculate_all_kpis\(",  # UI modules must consume pre-calculated kpis dict
    ]

    for file_path in target_files:
        assert file_path.is_file(), f"Target file does not exist: {file_path}"
        content = file_path.read_text(encoding="utf-8")

        for pattern in prohibited_patterns:
            matches = re.findall(pattern, content)
            assert not matches, (
                f"Found prohibited formula pattern '{pattern}' in {file_path.name}. "
                "Phase 2.5 files must consume KPI outputs from kpi_engine.py."
            )

