"""
Standardized Five-KPI Calculation Engine.
Manufacturing Diagnostic Intelligence System - Phase 2.

This module provides a headless, vectorized, reusable, and testable calculation
engine for the five strategic KPI domains defined in the Phase 2.0 Scope Freeze:
1. Machine Health Tracking (Separate Indicators: Temp, Vib, PM Score)
2. Operational Throughput Rate (Fleet & Mode-Stratified Production Speed in units/hr)
3. Product Quality (Defect Rate & Arithmetic Complement: 94.991194%)
4. Telemetry Reliability Tracking (Network Latency, Packet Loss, Within-Machine Jitter)
5. Energy-Adjusted Efficiency (Row-Level SEC in kWh/unit & Empirical Status Breakdown)

Design Principles:
- Headless Python module (pure computation, no UI or Streamlit dependencies).
- Vectorized operations using pandas and numpy.
- Does NOT mutate input DataFrames.
- Validates input schemas and handles edge cases gracefully.
- Strict adherence to Phase 2.0 provisional safeguards and non-goals.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple, Union

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Custom Exceptions
# ---------------------------------------------------------------------------

class KPIEngineError(Exception):
    """Base exception for all KPI calculation errors."""
    pass


class InvalidInputDataError(KPIEngineError):
    """Raised when input DataFrame is missing required columns, empty, or structurally invalid."""
    pass


# ---------------------------------------------------------------------------
# Helper Calculation Functions
# ---------------------------------------------------------------------------

def _calculate_descriptive_stats(series: pd.Series, unit: str = "") -> Dict[str, Any]:
    """
    Calculate standardized descriptive statistics for a numeric pandas Series.

    Calculates:
    - count (int)
    - mean (float)
    - median (float)
    - std_dev (float, ddof=1)
    - std (alias for std_dev)
    - min (float)
    - max (float)
    - p50 (float, 50th percentile)
    - p90 (float, 90th percentile)
    - p95 (float, 95th percentile)
    - p99 (float, 99th percentile)
    - unit (str)

    Parameters:
        series: Pandas numeric Series.
        unit: Measurement unit string.

    Returns:
        Dictionary of computed descriptive statistics.
    """
    clean_series = series.dropna()
    n = len(clean_series)

    if n == 0:
        return {
            "count": 0,
            "mean": float("nan"),
            "median": float("nan"),
            "std_dev": float("nan"),
            "std": float("nan"),
            "min": float("nan"),
            "max": float("nan"),
            "p50": float("nan"),
            "p90": float("nan"),
            "p95": float("nan"),
            "p99": float("nan"),
            "unit": unit,
        }

    mean_val = float(clean_series.mean())
    median_val = float(clean_series.median())
    std_val = float(clean_series.std(ddof=1)) if n > 1 else float("nan")
    min_val = float(clean_series.min())
    max_val = float(clean_series.max())

    # Quantiles using standard linear interpolation
    quantiles = clean_series.quantile([0.5, 0.9, 0.95, 0.99]).to_dict()

    return {
        "count": n,
        "mean": mean_val,
        "median": median_val,
        "std_dev": std_val,
        "std": std_val,
        "min": min_val,
        "max": max_val,
        "p50": float(quantiles[0.5]),
        "p90": float(quantiles[0.9]),
        "p95": float(quantiles[0.95]),
        "p99": float(quantiles[0.99]),
        "unit": unit,
    }


def _validate_input_dataframe(df: pd.DataFrame, required_columns: List[str], function_name: str) -> None:
    """
    Validate that input is a non-empty pandas DataFrame containing all required columns.

    Parameters:
        df: Input object to validate.
        required_columns: List of column names that must exist in df.
        function_name: Name of the calling function for descriptive error reporting.

    Raises:
        InvalidInputDataError: If df is not a DataFrame, is empty, or lacks required columns.
    """
    if not isinstance(df, pd.DataFrame):
        raise InvalidInputDataError(
            f"[{function_name}] Invalid input type: expected pandas DataFrame, received {type(df).__name__}."
        )

    if df.empty:
        raise InvalidInputDataError(f"[{function_name}] Input DataFrame is empty (0 rows).")

    missing = [c for c in required_columns if c not in df.columns]
    if missing:
        raise InvalidInputDataError(
            f"[{function_name}] Missing required columns: {missing}. Present columns: {list(df.columns)}."
        )


# ---------------------------------------------------------------------------
# KPI 1 — Machine Health Tracking
# ---------------------------------------------------------------------------

def calculate_machine_health_kpi(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculate KPI Domain 1: Machine Health Tracking.

    Source Fields:
    - Temperature_C (°C)
    - Vibration_Hz (Hz)
    - Predictive_Maintenance_Score (dimensionless)

    Safeguards:
    - Calculates independent descriptive statistics for all three channels.
    - Does NOT compute a combined Machine Health Index.
    - Does NOT apply arbitrary normalization ranges or invented weights.
    - Does NOT establish alarm thresholds or classify machines as healthy/faulty.
    - Reports Predictive_Maintenance_Score as a neutral numerical indicator with
      direction/polarity explicitly flagged as unresolved.

    Parameters:
        df: Input DataFrame containing the source columns.

    Returns:
        Structured dictionary containing independent indicators, statistics, and metadata.
    """
    required = ["Temperature_C", "Vibration_Hz", "Predictive_Maintenance_Score"]
    _validate_input_dataframe(df, required, "calculate_machine_health_kpi")

    temp_stats = _calculate_descriptive_stats(df["Temperature_C"], unit="°C")
    vib_stats = _calculate_descriptive_stats(df["Vibration_Hz"], unit="Hz")
    pm_stats = _calculate_descriptive_stats(df["Predictive_Maintenance_Score"], unit="dimensionless")

    return {
        "domain": "Machine Health Tracking",
        "status": "PROVISIONAL",
        "composite_index_calculated": False,
        "safeguard_notes": (
            "Tracked strictly as three separate, unweighted, independent indicators. "
            "No composite Machine Health Index, arbitrary weights, or alarm thresholds are applied. "
            "Predictive_Maintenance_Score is reported as a neutral numerical indicator with polarity unresolved."
        ),
        "temperature_c": temp_stats,
        "vibration_hz": vib_stats,
        "predictive_maintenance_score": {
            **pm_stats,
            "polarity_interpretation": "unresolved_neutral",
            "polarity_caveat": (
                "Mathematical definition and polarity (0.0 = minimal risk vs. 1.0 = minimal risk) "
                "remain unverified in source documentation."
            ),
        },
    }


# ---------------------------------------------------------------------------
# KPI 2 — Operational Throughput Rate
# ---------------------------------------------------------------------------

def calculate_operational_throughput_kpi(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculate KPI Domain 2: Operational Throughput Rate (OTR).

    Source Fields:
    - Production_Speed_units_per_hr (units/hr)
    - Operation_Mode (Active, Idle, Maintenance)

    Safeguards:
    - Fleet-wide throughput includes all three recorded operation modes.
    - Idle and Maintenance records are NOT silently excluded from fleet metrics.
    - Observed maximum (~500 units/hr) is NOT treated as rated machine capacity.
    - Capacity utilization percentages are NOT calculated.
    - Throughput is reported strictly as empirical production speed in units/hr.

    Parameters:
        df: Input DataFrame containing the source columns.

    Returns:
        Structured dictionary containing fleet-wide and mode-stratified throughput statistics.
    """
    required = ["Production_Speed_units_per_hr", "Operation_Mode"]
    _validate_input_dataframe(df, required, "calculate_operational_throughput_kpi")

    # Fleet-wide statistics across all operation modes
    fleet_stats = _calculate_descriptive_stats(df["Production_Speed_units_per_hr"], unit="units/hr")

    # Mode-stratified breakdown
    modes = ["Active", "Idle", "Maintenance"]
    mode_stats: Dict[str, Dict[str, Any]] = {}
    for mode in modes:
        mode_series = df.loc[df["Operation_Mode"] == mode, "Production_Speed_units_per_hr"]
        if len(mode_series) > 0:
            mode_stats[mode] = _calculate_descriptive_stats(mode_series, unit="units/hr")
        else:
            mode_stats[mode] = {
                "count": 0,
                "mean": float("nan"),
                "median": float("nan"),
                "std_dev": float("nan"),
                "std": float("nan"),
                "min": float("nan"),
                "max": float("nan"),
                "p50": float("nan"),
                "p90": float("nan"),
                "p95": float("nan"),
                "p99": float("nan"),
                "unit": "units/hr",
            }

    return {
        "domain": "Operational Throughput Rate",
        "status": "PROVISIONAL",
        "unit": "units/hr",
        "capacity_utilization_calculated": False,
        "safeguard_notes": (
            "Includes all three recorded operation modes (Active, Idle, Maintenance) in fleet-wide metrics. "
            "Observed maximum is not treated as rated machine capacity. "
            "No capacity utilization or invented production targets are calculated."
        ),
        "fleet_throughput": fleet_stats,
        "mode_stratified_throughput": mode_stats,
    }


# ---------------------------------------------------------------------------
# KPI 3 — Product Quality
# ---------------------------------------------------------------------------

def calculate_product_quality_kpi(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculate KPI Domain 3: Product Quality.

    Source Fields:
    - Quality_Control_Defect_Rate_% (%)
    - Error_Rate_% (%)

    Safeguards:
    - Arithmetic complement is defined strictly as: 100 - Mean Defect Rate (%).
    - Arithmetic complement is NOT presented as verified first-pass yield, product conformance,
      process capability, or confirmed manufacturing yield.
    - Physical defective-piece counts, batch sizes, and scrap denominators are NOT invented.
    - Error_Rate_% is evaluated separately as a distinct process-error indicator.
    - Defect_Rate_% and Error_Rate_% are NOT combined into a composite quality score.

    Parameters:
        df: Input DataFrame containing the source columns.

    Returns:
        Structured dictionary containing defect rate, arithmetic complement, and error rate statistics.
    """
    required = ["Quality_Control_Defect_Rate_%", "Error_Rate_%"]
    _validate_input_dataframe(df, required, "calculate_product_quality_kpi")

    defect_stats = _calculate_descriptive_stats(df["Quality_Control_Defect_Rate_%"], unit="%")
    error_stats = _calculate_descriptive_stats(df["Error_Rate_%"], unit="%")

    mean_defect = defect_stats["mean"]
    arithmetic_complement_val = 100.0 - mean_defect if not np.isnan(mean_defect) else float("nan")

    return {
        "domain": "Product Quality",
        "status": "PROVISIONAL",
        "composite_quality_score_calculated": False,
        "defect_rate": defect_stats,
        "arithmetic_complement": {
            "value": arithmetic_complement_val,
            "unit": "%",
            "formula": "100 - Mean Defect Rate (%)",
            "description": "Arithmetic complement of the recorded mean defect rate.",
            "disclaimer": (
                "Strictly the mathematical complement (100 - mean defect rate) within this telemetry extract. "
                "Must NOT be interpreted as verified first-pass yield, product conformance, process capability, "
                "or confirmed manufacturing yield without batch size and inspection denominator metadata."
            ),
        },
        "process_error_rate": {
            **error_stats,
            "description": "Related process execution error rate, tracked separately from finished defect rate.",
        },
        "safeguard_notes": (
            "Arithmetic complement represents strictly 100 - mean defect rate. "
            "No physical piece counts, inspection batch sizes, or composite quality scores are computed."
        ),
    }


# ---------------------------------------------------------------------------
# KPI 4 — Telemetry Reliability Tracking
# ---------------------------------------------------------------------------

def calculate_telemetry_reliability_kpi(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculate KPI Domain 4: Telemetry Reliability Tracking.

    Source Fields:
    - Network_Latency_ms (ms)
    - Packet_Loss_% (%)
    - Machine_ID (1 to 50)

    Safeguards:
    - Evaluates Network_Latency_ms and Packet_Loss_% descriptive statistics independently.
    - Calculates within-machine latency dispersion (jitter) using sample standard deviation (ddof=1)
      per Machine_ID.
    - Handles groups with fewer than two observations explicitly without fabricating values (returns NaN).
    - Returns machine-level dispersion and fleet-level summary of machine dispersion.
    - Does NOT compute a composite telemetry reliability score.
    - Does NOT compute threshold-based SLA compliance percentages (e.g. 30ms or 1% loss cutoffs).
    - Does NOT create pass/fail classifications or invent 6G performance targets.

    Parameters:
        df: Input DataFrame containing the source columns.

    Returns:
        Structured dictionary containing network QoS statistics and within-machine jitter dispersion.
    """
    required = ["Network_Latency_ms", "Packet_Loss_%", "Machine_ID"]
    _validate_input_dataframe(df, required, "calculate_telemetry_reliability_kpi")

    lat_stats = _calculate_descriptive_stats(df["Network_Latency_ms"], unit="ms")
    loss_stats = _calculate_descriptive_stats(df["Packet_Loss_%"], unit="%")

    # Within-machine latency dispersion: sample standard deviation (ddof=1) per Machine_ID
    # Explicitly handles machine groups with < 2 observations: returns NaN without fabricating 0.0
    machine_groups = df.groupby("Machine_ID")["Network_Latency_ms"]
    machine_counts = machine_groups.count()
    machine_stds = machine_groups.std(ddof=1)

    machine_jitter_dict: Dict[int, Optional[float]] = {}
    valid_jitters: List[float] = []

    for m_id, n_obs in machine_counts.items():
        if n_obs < 2:
            machine_jitter_dict[int(m_id)] = None
        else:
            val = float(machine_stds.loc[m_id])
            machine_jitter_dict[int(m_id)] = val
            valid_jitters.append(val)

    # Fleet summary of within-machine jitter
    if valid_jitters:
        v_series = pd.Series(valid_jitters)
        fleet_jitter_summary = {
            "evaluated_machines_count": len(valid_jitters),
            "insufficient_data_machines_count": len(machine_counts) - len(valid_jitters),
            "mean": float(v_series.mean()),
            "median": float(v_series.median()),
            "std_dev": float(v_series.std(ddof=1)) if len(v_series) > 1 else float("nan"),
            "std": float(v_series.std(ddof=1)) if len(v_series) > 1 else float("nan"),
            "min": float(v_series.min()),
            "max": float(v_series.max()),
            "p50": float(v_series.quantile(0.5)),
            "p90": float(v_series.quantile(0.9)),
            "p95": float(v_series.quantile(0.95)),
            "p99": float(v_series.quantile(0.99)),
            "unit": "ms",
        }
    else:
        fleet_jitter_summary = {
            "evaluated_machines_count": 0,
            "insufficient_data_machines_count": len(machine_counts),
            "mean": float("nan"),
            "median": float("nan"),
            "std_dev": float("nan"),
            "std": float("nan"),
            "min": float("nan"),
            "max": float("nan"),
            "p50": float("nan"),
            "p90": float("nan"),
            "p95": float("nan"),
            "p99": float("nan"),
            "unit": "ms",
        }

    return {
        "domain": "Telemetry Reliability Tracking",
        "status": "PROVISIONAL",
        "composite_reliability_score_calculated": False,
        "sla_threshold_compliance_calculated": False,
        "safeguard_notes": (
            "Presented strictly as descriptive empirical network measurements. No composite reliability score, "
            "threshold-based SLA compliance percentages (e.g. 30ms or 1% loss cutoffs), or pass/fail classifications "
            "are computed. 6G performance targets remain unconfigured pending authoritative specifications."
        ),
        "network_latency": lat_stats,
        "packet_loss": loss_stats,
        "within_machine_jitter": {
            "definition": "Sample standard deviation (ddof=1) of Network_Latency_ms per Machine_ID.",
            "unit": "ms",
            "machine_jitter": machine_jitter_dict,
            "fleet_summary": fleet_jitter_summary,
        },
    }


# ---------------------------------------------------------------------------
# KPI 5 — Energy-Adjusted Efficiency
# ---------------------------------------------------------------------------

def calculate_energy_efficiency_kpi(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculate KPI Domain 5: Energy-Adjusted Efficiency (EAE).

    Source Fields:
    - Power_Consumption_kW (kW)
    - Production_Speed_units_per_hr (units/hr)
    - Efficiency_Status ('Low', 'Medium', 'High')

    Calculations:
    - Specific Energy Consumption (SEC) = Power_Consumption_kW / Production_Speed_units_per_hr (kWh/unit)
      evaluated strictly at row-level for positive speed observations (Production_Speed_units_per_hr > 0).
    - Summary of eligible and excluded records.
    - Descriptive statistics of row-level SEC (mean, median, std_dev, min, max, P50, P90, P95, P99).
    - Empirical category breakdown of recorded Efficiency_Status labels (counts and percentages).

    Safeguards:
    - SEC is calculated at individual-record level before descriptive statistics; never uses the ratio
      of fleet mean power to fleet mean speed.
    - Excludes non-positive speed records (speed <= 0) from the SEC calculation.
    - Does NOT calculate an invented weighted efficiency index.
    - Does NOT combine SEC with Efficiency_Status into a composite score.
    - Preserves recorded Efficiency_Status labels without reconstruction.
    - Explicitly includes the reconciliation note regarding the two boundary mismatches at Error_Rate_% = 5.0%.

    Parameters:
        df: Input DataFrame containing the source columns.

    Returns:
        Structured dictionary containing SEC descriptive statistics and Efficiency_Status breakdowns.
    """
    required = ["Power_Consumption_kW", "Production_Speed_units_per_hr", "Efficiency_Status"]
    _validate_input_dataframe(df, required, "calculate_energy_efficiency_kpi")

    power = df["Power_Consumption_kW"]
    speed = df["Production_Speed_units_per_hr"]

    # SEC is evaluated ONLY where production speed is strictly positive (> 0)
    eligible_mask = speed > 0
    eligible_count = int(eligible_mask.sum())
    excluded_count = int((~eligible_mask).sum())

    if eligible_count > 0:
        # Row-level vectorized SEC calculation
        sec_series = power[eligible_mask] / speed[eligible_mask]
        sec_stats = _calculate_descriptive_stats(sec_series, unit="kWh/unit")
    else:
        sec_stats = {
            "count": 0,
            "mean": float("nan"),
            "median": float("nan"),
            "std_dev": float("nan"),
            "std": float("nan"),
            "min": float("nan"),
            "max": float("nan"),
            "p50": float("nan"),
            "p90": float("nan"),
            "p95": float("nan"),
            "p99": float("nan"),
            "unit": "kWh/unit",
        }

    sec_summary = {
        "formula": "Power_Consumption_kW / Production_Speed_units_per_hr",
        "unit": "kWh/unit",
        "eligible_count": eligible_count,
        "excluded_count": excluded_count,
        **sec_stats,
    }

    # Empirical category breakdown for Efficiency_Status
    status_counts_raw = df["Efficiency_Status"].value_counts().to_dict()
    total_records = len(df)
    
    status_counts: Dict[str, int] = {
        "Low": int(status_counts_raw.get("Low", 0)),
        "Medium": int(status_counts_raw.get("Medium", 0)),
        "High": int(status_counts_raw.get("High", 0)),
    }
    status_percentages: Dict[str, float] = {
        k: (v / total_records * 100.0) if total_records > 0 else 0.0
        for k, v in status_counts.items()
    }

    return {
        "domain": "Energy-Adjusted Efficiency",
        "status": "PROVISIONAL",
        "composite_efficiency_score_calculated": False,
        "safeguard_notes": (
            "Specific Energy Consumption (SEC) is evaluated strictly at row-level for positive production speed "
            "(Production_Speed_units_per_hr > 0). No composite weighted score combining SEC with Efficiency_Status "
            "is computed. Efficiency_Status is reported as an empirical categorical breakdown with recorded labels "
            "preserved without reconstruction."
        ),
        "specific_energy_consumption": sec_summary,
        "efficiency_status_breakdown": {
            "clarification": (
                "The Efficiency_Status generation logic is not independently verified. The accepted Phase 1 "
                "reconciliation identified exactly two candidate classification mismatches at Error_Rate_% = 5.0%. "
                "Recorded labels are preserved without reconstruction."
            ),
            "counts": status_counts,
            "percentages": status_percentages,
            "total_records": total_records,
        },
    }


# ---------------------------------------------------------------------------
# Orchestration Function
# ---------------------------------------------------------------------------

def calculate_all_kpis(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Orchestrate the calculation of all five strategic KPI domains.

    Executes:
    1. Machine Health Tracking
    2. Operational Throughput Rate
    3. Product Quality
    4. Telemetry Reliability Tracking
    5. Energy-Adjusted Efficiency

    Parameters:
        df: Input DataFrame containing all required source columns across all domains.

    Returns:
        Structured dictionary containing outputs for all five KPI domains.

    Raises:
        InvalidInputDataError: If df is not a DataFrame, is empty, or lacks required columns.
    """
    all_required = [
        "Temperature_C",
        "Vibration_Hz",
        "Predictive_Maintenance_Score",
        "Production_Speed_units_per_hr",
        "Operation_Mode",
        "Quality_Control_Defect_Rate_%",
        "Error_Rate_%",
        "Network_Latency_ms",
        "Packet_Loss_%",
        "Machine_ID",
        "Power_Consumption_kW",
        "Efficiency_Status",
    ]
    _validate_input_dataframe(df, all_required, "calculate_all_kpis")

    return {
        "machine_health": calculate_machine_health_kpi(df),
        "operational_throughput": calculate_operational_throughput_kpi(df),
        "product_quality": calculate_product_quality_kpi(df),
        "telemetry_reliability": calculate_telemetry_reliability_kpi(df),
        "energy_efficiency": calculate_energy_efficiency_kpi(df),
    }


# ---------------------------------------------------------------------------
# CLI Direct Execution Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    from pathlib import Path
    _proj_root = Path(__file__).resolve().parent.parent.parent
    if str(_proj_root) not in sys.path:
        sys.path.insert(0, str(_proj_root))

    print("=" * 75)
    print("STANDARDIZED FIVE-KPI CALCULATION ENGINE (PHASE 2.2)")
    print("=" * 75)

    try:
        from scripts.app.data_loader import load_manufacturing_data

        print("\n[1] Loading validated dataset via data_loader...")
        df_loaded = load_manufacturing_data(validate=True)
        print(f"    Loaded dataset: {len(df_loaded):,} rows x {len(df_loaded.columns)} columns.")

        print("\n[2] Executing calculate_all_kpis(df)...")
        results = calculate_all_kpis(df_loaded)

        mh = results["machine_health"]
        otr = results["operational_throughput"]
        pq = results["product_quality"]
        tr = results["telemetry_reliability"]
        ee = results["energy_efficiency"]

        print("\n" + "-" * 75)
        print("KPI 1: MACHINE HEALTH TRACKING")
        print("-" * 75)
        print(f"  - Temperature (°C): mean={mh['temperature_c']['mean']:.4f}, median={mh['temperature_c']['median']:.4f}, std={mh['temperature_c']['std_dev']:.4f}")
        print(f"  - Vibration (Hz):   mean={mh['vibration_hz']['mean']:.4f}, median={mh['vibration_hz']['median']:.4f}, std={mh['vibration_hz']['std_dev']:.4f}")
        print(f"  - PM Score:         mean={mh['predictive_maintenance_score']['mean']:.4f}, median={mh['predictive_maintenance_score']['median']:.4f}, std={mh['predictive_maintenance_score']['std_dev']:.4f}")

        print("\n" + "-" * 75)
        print("KPI 2: OPERATIONAL THROUGHPUT RATE")
        print("-" * 75)
        print(f"  - Fleet Mean Speed: {otr['fleet_throughput']['mean']:.4f} units/hr (median: {otr['fleet_throughput']['median']:.4f})")
        for mode, m_data in otr["mode_stratified_throughput"].items():
            print(f"  - Mode '{mode}': count={m_data['count']:,}, mean={m_data['mean']:.4f} units/hr")

        print("\n" + "-" * 75)
        print("KPI 3: PRODUCT QUALITY")
        print("-" * 75)
        print(f"  - Mean Defect Rate:        {pq['defect_rate']['mean']:.6f}%")
        print(f"  - Arithmetic Complement:   {pq['arithmetic_complement']['value']:.6f}% ({pq['arithmetic_complement']['description']})")
        print(f"  - Process Error Rate Mean: {pq['process_error_rate']['mean']:.6f}%")

        print("\n" + "-" * 75)
        print("KPI 4: TELEMETRY RELIABILITY TRACKING")
        print("-" * 75)
        print(f"  - Network Latency: mean={tr['network_latency']['mean']:.4f} ms (median: {tr['network_latency']['median']:.4f} ms)")
        print(f"  - Packet Loss:    mean={tr['packet_loss']['mean']:.4f}% (median: {tr['packet_loss']['median']:.4f}%)")
        f_jit = tr["within_machine_jitter"]["fleet_summary"]
        print(f"  - Machine Jitter: evaluated={f_jit['evaluated_machines_count']} machines, fleet mean jitter={f_jit['mean']:.4f} ms [range: {f_jit['min']:.4f} - {f_jit['max']:.4f} ms]")

        print("\n" + "-" * 75)
        print("KPI 5: ENERGY-ADJUSTED EFFICIENCY")
        print("-" * 75)
        sec = ee["specific_energy_consumption"]
        print(f"  - Specific Energy Consumption: eligible={sec['eligible_count']:,}, excluded={sec['excluded_count']:,}")
        print(f"    mean={sec['mean']:.6f} kWh/unit, median={sec['median']:.6f} kWh/unit, std={sec['std_dev']:.6f}")
        brk = ee["efficiency_status_breakdown"]
        print(f"  - Efficiency Status Counts: Low={brk['counts']['Low']:,} ({brk['percentages']['Low']:.3f}%), "
              f"Medium={brk['counts']['Medium']:,} ({brk['percentages']['Medium']:.3f}%), "
              f"High={brk['counts']['High']:,} ({brk['percentages']['High']:.3f}%)")

        print("\n" + "=" * 75)
        print("STANDARDIZED FIVE-KPI CALCULATION ENGINE: VERIFICATION READY")
        print("=" * 75)
    except Exception as exc:
        print(f"\n[ERROR] KPI Engine Execution Failure: {exc}")
        raise
