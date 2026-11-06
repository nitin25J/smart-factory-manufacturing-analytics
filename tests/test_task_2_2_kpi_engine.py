"""
Unit and Integration Tests for Standardized Five-KPI Calculation Engine.
Task 2.2 - Manufacturing Diagnostic Intelligence System.

Tests verify:
1. Correct machine-health indicator calculations.
2. No composite machine-health index.
3. Predictive maintenance score remains direction-neutral.
4. Fleet-wide throughput uses all three operation modes.
5. Correct mode-stratified throughput summaries.
6. No capacity-utilization calculations.
7. Correct arithmetic defect-rate complement.
8. Error rate remains a separate descriptive metric.
9. Quality output does not claim verified yield.
10. Network latency and packet-loss statistics.
11. Correct P50, P90, P95 and P99 calculations.
12. Correct within-machine jitter using sample standard deviation.
13. No SLA threshold classifications.
14. Correct row-level SEC calculation.
15. Non-positive production-speed records excluded from SEC.
16. Correct Efficiency_Status category counts and percentages.
17. No reconstructed Efficiency_Status labels.
18. Input DataFrame remains unchanged.
19. Missing-column and invalid-input handling.
20. KPI orchestration returns all five domains.
"""

from __future__ import annotations

import math
from typing import Dict, List

import numpy as np
import pandas as pd
import pytest

from scripts.app.data_loader import load_manufacturing_data
from scripts.app.kpi_engine import (
    InvalidInputDataError,
    KPIEngineError,
    calculate_all_kpis,
    calculate_energy_efficiency_kpi,
    calculate_machine_health_kpi,
    calculate_operational_throughput_kpi,
    calculate_product_quality_kpi,
    calculate_telemetry_reliability_kpi,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def loaded_dataframe() -> pd.DataFrame:
    """Load the full valid dataset once for module-level non-mutating assertions."""
    return load_manufacturing_data(validate=True)


@pytest.fixture
def minimal_kpi_df() -> pd.DataFrame:
    """Create a minimal valid synthetic DataFrame containing all 12 KPI columns."""
    data = {
        "Machine_ID": [1, 1, 2, 2],
        "Operation_Mode": ["Active", "Idle", "Active", "Maintenance"],
        "Temperature_C": [60.0, 70.0, 50.0, 80.0],
        "Vibration_Hz": [2.0, 3.0, 1.5, 4.0],
        "Power_Consumption_kW": [5.0, 6.0, 4.0, 8.0],
        "Network_Latency_ms": [20.0, 22.0, 30.0, 34.0],
        "Packet_Loss_%": [2.0, 1.0, 3.0, 4.0],
        "Quality_Control_Defect_Rate_%": [4.0, 6.0, 5.0, 5.0],
        "Production_Speed_units_per_hr": [200.0, 300.0, 100.0, 400.0],
        "Predictive_Maintenance_Score": [0.4, 0.6, 0.3, 0.7],
        "Error_Rate_%": [6.0, 8.0, 7.0, 9.0],
        "Efficiency_Status": ["Low", "Medium", "Low", "High"],
    }
    return pd.DataFrame(data)


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

def test_01_machine_health_indicator_calculations(loaded_dataframe: pd.DataFrame) -> None:
    """
    Test 1: Verify correct descriptive statistics for all three machine health indicators.
    Reconciles with Phase 1 baseline values:
    - Temperature mean ~ 60.0415 C
    - Vibration mean ~ 2.5500 Hz
    - Predictive Maintenance Score mean ~ 0.4994
    """
    result = calculate_machine_health_kpi(loaded_dataframe)
    assert result["domain"] == "Machine Health Tracking"
    assert result["status"] == "PROVISIONAL"

    # Temperature
    temp = result["temperature_c"]
    assert temp["count"] == 100000
    assert pytest.approx(temp["mean"], abs=1e-4) == 60.0415
    assert pytest.approx(temp["median"], abs=1e-4) == 60.0335
    assert pytest.approx(temp["std_dev"], abs=1e-4) == 17.3232
    assert temp["min"] >= 0.0
    assert temp["unit"] == "°C"

    # Vibration
    vib = result["vibration_hz"]
    assert vib["count"] == 100000
    assert pytest.approx(vib["mean"], abs=1e-4) == 2.5500
    assert pytest.approx(vib["median"], abs=1e-4) == 2.5490
    assert pytest.approx(vib["std_dev"], abs=1e-4) == 1.4141
    assert vib["unit"] == "Hz"

    # Predictive Maintenance Score
    pm = result["predictive_maintenance_score"]
    assert pm["count"] == 100000
    assert pytest.approx(pm["mean"], abs=1e-4) == 0.4994
    assert pytest.approx(pm["median"], abs=1e-4) == 0.4990
    assert pytest.approx(pm["std_dev"], abs=1e-4) == 0.2888
    assert pm["unit"] == "dimensionless"


def test_02_no_composite_machine_health_index(loaded_dataframe: pd.DataFrame) -> None:
    """
    Test 2: Verify that no composite Machine Health Index is calculated.
    Ensures indicators remain strictly separate without invented weights or alarms.
    """
    result = calculate_machine_health_kpi(loaded_dataframe)
    assert result["composite_index_calculated"] is False
    assert "machine_health_index" not in result
    assert "mhi" not in result
    assert "composite_health_score" not in result
    assert "health_score" not in result
    assert "composite_score" not in result


def test_03_predictive_maintenance_score_direction_neutral(loaded_dataframe: pd.DataFrame) -> None:
    """
    Test 3: Verify predictive maintenance score remains reported as a neutral numerical indicator.
    Ensures no healthy/faulty machine classification is made.
    """
    result = calculate_machine_health_kpi(loaded_dataframe)
    pm = result["predictive_maintenance_score"]
    assert pm["polarity_interpretation"] == "unresolved_neutral"
    assert "unverified" in pm["polarity_caveat"].lower()
    # No healthy/degraded classifications
    assert "healthy_machines" not in pm
    assert "faulty_machines" not in pm
    assert "alarm_triggered" not in pm


def test_04_fleet_throughput_uses_all_three_operation_modes(loaded_dataframe: pd.DataFrame) -> None:
    """
    Test 4: Verify fleet-wide throughput includes all 100,000 observations across Active, Idle, Maintenance.
    Reconciles with Phase 1 baseline: 275.9163 units/hr.
    """
    result = calculate_operational_throughput_kpi(loaded_dataframe)
    fleet = result["fleet_throughput"]
    assert fleet["count"] == 100000
    assert pytest.approx(fleet["mean"], abs=1e-4) == 275.9163
    assert pytest.approx(fleet["median"], abs=1e-4) == 276.6490
    assert pytest.approx(fleet["std_dev"], abs=1e-4) == 130.0969
    assert fleet["unit"] == "units/hr"


def test_05_correct_mode_stratified_throughput_summaries(loaded_dataframe: pd.DataFrame) -> None:
    """
    Test 5: Verify mode-stratified throughput summaries match accepted Phase 1 baselines:
    - Active: 70,054 records, mean 276.1993 units/hr
    - Idle: 20,057 records, mean 274.1256 units/hr
    - Maintenance: 9,889 records, mean 277.5440 units/hr
    """
    result = calculate_operational_throughput_kpi(loaded_dataframe)
    modes = result["mode_stratified_throughput"]
    
    assert modes["Active"]["count"] == 70054
    assert pytest.approx(modes["Active"]["mean"], abs=1e-4) == 276.1993

    assert modes["Idle"]["count"] == 20057
    assert pytest.approx(modes["Idle"]["mean"], abs=1e-4) == 274.1256

    assert modes["Maintenance"]["count"] == 9889
    assert pytest.approx(modes["Maintenance"]["mean"], abs=1e-4) == 277.5440


def test_06_no_capacity_utilization_calculations(loaded_dataframe: pd.DataFrame) -> None:
    """
    Test 6: Verify capacity utilization percentages and targets are NOT calculated.
    """
    result = calculate_operational_throughput_kpi(loaded_dataframe)
    assert result["capacity_utilization_calculated"] is False
    assert "capacity_utilization" not in result
    assert "utilization_pct" not in result
    assert "rated_capacity" not in result


def test_07_correct_arithmetic_defect_rate_complement(loaded_dataframe: pd.DataFrame) -> None:
    """
    Test 7: Verify arithmetic complement of mean defect rate:
    Formula: 100 - Mean Defect Rate (%)
    Mean defect: 5.008806% -> Complement: 94.991194%
    """
    result = calculate_product_quality_kpi(loaded_dataframe)
    defect = result["defect_rate"]
    assert defect["count"] == 100000
    assert pytest.approx(defect["mean"], abs=1e-6) == 5.008806

    comp = result["arithmetic_complement"]
    assert pytest.approx(comp["value"], abs=1e-6) == 94.991194
    assert comp["unit"] == "%"
    assert comp["formula"] == "100 - Mean Defect Rate (%)"


def test_08_error_rate_remains_separate_descriptive_metric(loaded_dataframe: pd.DataFrame) -> None:
    """
    Test 8: Verify Error_Rate_% is calculated separately as a related process-error indicator.
    Mean error rate ~ 7.504101%.
    No composite defect-error score is generated.
    """
    result = calculate_product_quality_kpi(loaded_dataframe)
    error = result["process_error_rate"]
    assert error["count"] == 100000
    assert pytest.approx(error["mean"], abs=1e-6) == 7.504101
    assert result["composite_quality_score_calculated"] is False
    assert "composite_quality_score" not in result
    assert "quality_index" not in result


def test_09_quality_output_does_not_claim_verified_yield(loaded_dataframe: pd.DataFrame) -> None:
    """
    Test 9: Verify arithmetic complement is explicitly described with strict disclaimer
    not claiming verified first-pass yield, product conformance, or process capability.
    """
    result = calculate_product_quality_kpi(loaded_dataframe)
    comp = result["arithmetic_complement"]
    assert comp["description"] == "Arithmetic complement of the recorded mean defect rate."
    disclaimer = comp["disclaimer"]
    assert "not" in disclaimer.lower()
    assert "first-pass yield" in disclaimer.lower()
    assert "product conformance" in disclaimer.lower()
    assert "process capability" in disclaimer.lower()


def test_10_network_latency_and_packet_loss_statistics(loaded_dataframe: pd.DataFrame) -> None:
    """
    Test 10: Verify network latency and packet loss statistics:
    - Mean Latency ~ 25.5556 ms (median ~ 25.5360 ms)
    - Mean Loss ~ 2.4934% (median ~ 2.4880%)
    """
    result = calculate_telemetry_reliability_kpi(loaded_dataframe)
    lat = result["network_latency"]
    assert lat["count"] == 100000
    assert pytest.approx(lat["mean"], abs=1e-4) == 25.5556
    assert pytest.approx(lat["median"], abs=1e-4) == 25.5360
    assert lat["unit"] == "ms"

    loss = result["packet_loss"]
    assert loss["count"] == 100000
    assert pytest.approx(loss["mean"], abs=1e-4) == 2.4934
    assert pytest.approx(loss["median"], abs=1e-4) == 2.4880
    assert loss["unit"] == "%"


def test_11_correct_percentiles_calculation(loaded_dataframe: pd.DataFrame) -> None:
    """
    Test 11: Verify correct P50, P90, P95, and P99 calculation across metrics.
    Ensures P50 matches median and percentiles are monotonically non-decreasing.
    """
    result = calculate_machine_health_kpi(loaded_dataframe)
    temp = result["temperature_c"]
    assert temp["p50"] == temp["median"]
    assert temp["p50"] <= temp["p90"] <= temp["p95"] <= temp["p99"]

    # Verify on minimal synthetic known distribution
    s = pd.Series(range(1, 101))  # 1 to 100
    from scripts.app.kpi_engine import _calculate_descriptive_stats
    stats = _calculate_descriptive_stats(s)
    assert pytest.approx(stats["p50"]) == 50.5
    assert pytest.approx(stats["p90"]) == 90.1
    assert pytest.approx(stats["p95"]) == 95.05
    assert pytest.approx(stats["p99"]) == 99.01


def test_12_within_machine_jitter_sample_std(loaded_dataframe: pd.DataFrame) -> None:
    """
    Test 12: Verify within-machine latency dispersion using sample standard deviation (ddof=1).
    Reconciles with Phase 1 Task 1.8 findings:
    - Fleet mean jitter across 50 machines ~ 14.1206 ms
    - Jitter range ~ 13.8415 ms to 14.4299 ms
    Also verifies handling of groups with < 2 records without fabricating values.
    """
    result = calculate_telemetry_reliability_kpi(loaded_dataframe)
    jitter = result["within_machine_jitter"]
    assert jitter["unit"] == "ms"
    assert len(jitter["machine_jitter"]) == 50

    fleet_summary = jitter["fleet_summary"]
    assert fleet_summary["evaluated_machines_count"] == 50
    assert fleet_summary["insufficient_data_machines_count"] == 0
    assert pytest.approx(fleet_summary["mean"], abs=1e-4) == 14.1206
    assert pytest.approx(fleet_summary["min"], abs=1e-4) == 13.8415
    assert pytest.approx(fleet_summary["max"], abs=1e-4) == 14.4299

    # Test edge case: machine with single observation (<2) must return None/NaN, not 0.0
    df_single = pd.DataFrame({
        "Network_Latency_ms": [25.0],
        "Packet_Loss_%": [1.0],
        "Machine_ID": [99],
    })
    res_single = calculate_telemetry_reliability_kpi(df_single)
    single_jitter = res_single["within_machine_jitter"]["machine_jitter"][99]
    assert single_jitter is None, "Machines with < 2 observations must have None jitter without fabricating 0.0"
    assert res_single["within_machine_jitter"]["fleet_summary"]["insufficient_data_machines_count"] == 1


def test_13_no_sla_threshold_classifications(loaded_dataframe: pd.DataFrame) -> None:
    """
    Test 13: Verify that candidate SLA thresholds (e.g. 30ms, 1% loss) are NOT hardcoded as compliance engines.
    """
    result = calculate_telemetry_reliability_kpi(loaded_dataframe)
    assert result["composite_reliability_score_calculated"] is False
    assert result["sla_threshold_compliance_calculated"] is False
    assert "latency_sla_met" not in result
    assert "packet_loss_sla_met" not in result
    assert "pass_fail_rating" not in result


def test_14_row_level_sec_calculation(loaded_dataframe: pd.DataFrame) -> None:
    """
    Test 14: Verify Specific Energy Consumption (SEC) is calculated at the row level:
    SEC = Power_Consumption_kW / Production_Speed_units_per_hr (kWh/unit)
    Confirms mean of row-level SEC ~ 0.029311 kWh/unit, NOT ratio of fleet means (~0.02082 kWh/unit).
    """
    result = calculate_energy_efficiency_kpi(loaded_dataframe)
    sec = result["specific_energy_consumption"]
    assert sec["eligible_count"] == 100000
    assert sec["excluded_count"] == 0
    assert sec["unit"] == "kWh/unit"
    assert pytest.approx(sec["mean"], abs=1e-5) == 0.029311
    assert pytest.approx(sec["median"], abs=1e-5) == 0.020815

    # Confirm it is fundamentally different from ratio of fleet means
    fleet_mean_power = loaded_dataframe["Power_Consumption_kW"].mean()
    fleet_mean_speed = loaded_dataframe["Production_Speed_units_per_hr"].mean()
    ratio_of_means = fleet_mean_power / fleet_mean_speed
    assert abs(sec["mean"] - ratio_of_means) > 0.005, (
        "Row-level SEC mean must not be substituted by ratio of fleet means."
    )


def test_15_non_positive_speed_records_excluded_from_sec() -> None:
    """
    Test 15: Verify non-positive production-speed records (speed <= 0) are excluded from SEC.
    """
    df_synthetic = pd.DataFrame({
        "Power_Consumption_kW": [5.0, 6.0, 7.0, 8.0],
        "Production_Speed_units_per_hr": [100.0, 0.0, -50.0, 200.0],  # 2 positive, 1 zero, 1 negative
        "Efficiency_Status": ["Low", "Low", "Medium", "High"],
    })
    result = calculate_energy_efficiency_kpi(df_synthetic)
    sec = result["specific_energy_consumption"]
    assert sec["eligible_count"] == 2
    assert sec["excluded_count"] == 2

    # Eligible rows: (5.0 / 100.0 = 0.05) and (8.0 / 200.0 = 0.04) -> mean = 0.045
    assert pytest.approx(sec["mean"], abs=1e-6) == 0.045
    assert pytest.approx(sec["min"], abs=1e-6) == 0.04
    assert pytest.approx(sec["max"], abs=1e-6) == 0.05


def test_16_efficiency_status_category_counts_and_percentages(loaded_dataframe: pd.DataFrame) -> None:
    """
    Test 16: Verify Efficiency_Status category breakdown matches Phase 1 audit:
    - Low: 77,825 (77.825%)
    - Medium: 19,189 (19.189%)
    - High: 2,986 (2.986%)
    - Total: 100,000
    """
    result = calculate_energy_efficiency_kpi(loaded_dataframe)
    status_info = result["efficiency_status_breakdown"]
    counts = status_info["counts"]
    pcts = status_info["percentages"]

    assert counts["Low"] == 77825
    assert counts["Medium"] == 19189
    assert counts["High"] == 2986
    assert status_info["total_records"] == 100000

    assert pytest.approx(pcts["Low"], abs=1e-3) == 77.825
    assert pytest.approx(pcts["Medium"], abs=1e-3) == 19.189
    assert pytest.approx(pcts["High"], abs=1e-3) == 2.986


def test_17_no_reconstructed_efficiency_status_labels(loaded_dataframe: pd.DataFrame) -> None:
    """
    Test 17: Verify Efficiency_Status labels are preserved without reconstruction and
    the 2 candidate boundary mismatches at Error_Rate_% = 5.0% are explicitly documented.
    """
    result = calculate_energy_efficiency_kpi(loaded_dataframe)
    clarification = result["efficiency_status_breakdown"]["clarification"]
    assert "not independently verified" in clarification.lower()
    assert "two candidate classification mismatches" in clarification.lower()
    assert "5.0%" in clarification


def test_18_input_dataframe_immutability(loaded_dataframe: pd.DataFrame) -> None:
    """
    Test 18: Verify input DataFrame remains completely unchanged after executing all KPI functions.
    """
    df_snapshot = loaded_dataframe.copy(deep=True)
    
    # Run all KPI functions
    calculate_all_kpis(loaded_dataframe)
    calculate_machine_health_kpi(loaded_dataframe)
    calculate_operational_throughput_kpi(loaded_dataframe)
    calculate_product_quality_kpi(loaded_dataframe)
    calculate_telemetry_reliability_kpi(loaded_dataframe)
    calculate_energy_efficiency_kpi(loaded_dataframe)

    pd.testing.assert_frame_equal(loaded_dataframe, df_snapshot)


def test_19_missing_columns_and_invalid_input_handling(minimal_kpi_df: pd.DataFrame) -> None:
    """
    Test 19: Verify robust error handling for missing columns, empty DataFrames, and non-DataFrame types.
    """
    # Non-DataFrame input
    with pytest.raises(InvalidInputDataError, match="expected pandas DataFrame"):
        calculate_machine_health_kpi("not a dataframe")  # type: ignore

    # Empty DataFrame
    with pytest.raises(InvalidInputDataError, match="Input DataFrame is empty"):
        calculate_machine_health_kpi(pd.DataFrame())

    # Missing column in Machine Health
    df_no_temp = minimal_kpi_df.drop(columns=["Temperature_C"])
    with pytest.raises(InvalidInputDataError, match="Missing required columns.*Temperature_C"):
        calculate_machine_health_kpi(df_no_temp)

    # Missing column in Operational Throughput
    df_no_speed = minimal_kpi_df.drop(columns=["Production_Speed_units_per_hr"])
    with pytest.raises(InvalidInputDataError, match="Missing required columns.*Production_Speed_units_per_hr"):
        calculate_operational_throughput_kpi(df_no_speed)

    # Missing column in Product Quality
    df_no_defect = minimal_kpi_df.drop(columns=["Quality_Control_Defect_Rate_%"])
    with pytest.raises(InvalidInputDataError, match="Missing required columns.*Quality_Control_Defect_Rate_%"):
        calculate_product_quality_kpi(df_no_defect)

    # Missing column in Telemetry Reliability
    df_no_lat = minimal_kpi_df.drop(columns=["Network_Latency_ms"])
    with pytest.raises(InvalidInputDataError, match="Missing required columns.*Network_Latency_ms"):
        calculate_telemetry_reliability_kpi(df_no_lat)

    # Missing column in Energy Efficiency
    df_no_power = minimal_kpi_df.drop(columns=["Power_Consumption_kW"])
    with pytest.raises(InvalidInputDataError, match="Missing required columns.*Power_Consumption_kW"):
        calculate_energy_efficiency_kpi(df_no_power)


def test_20_kpi_orchestration_returns_all_five_domains(loaded_dataframe: pd.DataFrame) -> None:
    """
    Test 20: Verify calculate_all_kpis orchestrates all five KPI domains and returns structured dictionary.
    """
    results = calculate_all_kpis(loaded_dataframe)
    expected_domains = {
        "machine_health",
        "operational_throughput",
        "product_quality",
        "telemetry_reliability",
        "energy_efficiency",
    }
    assert set(results.keys()) == expected_domains

    # Ensure deterministic execution across calls
    results2 = calculate_all_kpis(loaded_dataframe)
    assert results["operational_throughput"]["fleet_throughput"]["mean"] == results2["operational_throughput"]["fleet_throughput"]["mean"]
    assert results["product_quality"]["arithmetic_complement"]["value"] == results2["product_quality"]["arithmetic_complement"]["value"]
    assert results["energy_efficiency"]["specific_energy_consumption"]["mean"] == results2["energy_efficiency"]["specific_energy_consumption"]["mean"]
