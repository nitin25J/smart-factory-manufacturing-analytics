"""
Analytics and Statistical Calculation Utilities.
Manufacturing Diagnostic Intelligence System — Phase 2.4.

This module provides reusable, vectorized, deterministic analytical helper
functions for dashboard visualization and diagnostics:
- Empirical Cumulative Distribution Function (ECDF) calculation.
- Within-machine latency dispersion (jitter) profiling and ranking.
- Machine-level comparative network telemetry aggregations.
- Bivariate / multivariate Mahalanobis distance statistical outlier screening.
- Machine-level mechanical condition summaries.

Design Principles:
- Strictly decoupled from UI/Streamlit rendering components.
- Fully vectorized using NumPy and Pandas.
- Pure functions: does NOT mutate input DataFrames.
- Defensive against empty slices, zero-variance columns, and small sample sizes.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from scipy import stats


# ---------------------------------------------------------------------------
# 1. Empirical Cumulative Distribution Function (ECDF)
# ---------------------------------------------------------------------------

def compute_ecdf(
    data: Union[pd.Series, np.ndarray, List[float]],
    max_points: int = 1000,
) -> pd.DataFrame:
    """
    Compute Empirical Cumulative Distribution Function (ECDF) coordinates.

    For an input sample X of size N, the ECDF is defined as:
        F_n(x) = (1 / N) * sum(I(X_i <= x))

    To maintain high-performance, responsive Plotly rendering on large samples
    (e.g., N = 100,000), this function decimate coordinates to at most
    `max_points` evenly spaced quantile steps while preserving the exact
    extrema (min, max) and distribution profile.

    Parameters:
        data: Numeric sequence or Series.
        max_points: Maximum number of coordinate points to return (default: 1000).

    Returns:
        DataFrame with columns:
            - 'value': Ordered measurement values (x-axis).
            - 'ecdf': Cumulative empirical probability in [0.0, 1.0] (y-axis).
            - 'percentile': Cumulative empirical percentage in [0.0, 100.0]%.
    """
    if isinstance(data, pd.Series):
        clean_arr = data.dropna().to_numpy(dtype=float)
    else:
        arr = np.asarray(data, dtype=float)
        clean_arr = arr[~np.isnan(arr)]

    n = len(clean_arr)
    if n == 0:
        return pd.DataFrame(columns=["value", "ecdf", "percentile"])

    sorted_vals = np.sort(clean_arr)
    cum_probs = np.arange(1, n + 1, dtype=float) / float(n)

    if n <= max_points:
        return pd.DataFrame({
            "value": sorted_vals,
            "ecdf": cum_probs,
            "percentile": cum_probs * 100.0,
        })

    # Evenly space indices to decimate while strictly capturing min and max
    indices = np.linspace(0, n - 1, num=max_points, dtype=int)
    # Ensure last index is exactly n - 1
    indices[-1] = n - 1

    return pd.DataFrame({
        "value": sorted_vals[indices],
        "ecdf": cum_probs[indices],
        "percentile": cum_probs[indices] * 100.0,
    })


# ---------------------------------------------------------------------------
# 2. Within-Machine Jitter and Telemetry Rankings (Module 1)
# ---------------------------------------------------------------------------

def compute_within_machine_jitter(
    df: pd.DataFrame,
    latency_col: str = "Network_Latency_ms",
    machine_col: str = "Machine_ID",
) -> pd.DataFrame:
    """
    Calculate within-machine latency delay dispersion (sample std dev s_m, ddof=1).

    Ranks machines from lowest jitter (Rank 1 = most stable transmission delay)
    to highest jitter across the observed machine fleet.

    Parameters:
        df: Input telemetry DataFrame.
        latency_col: Column name for network latency.
        machine_col: Column name for machine identifier.

    Returns:
        DataFrame with columns:
            - 'Machine_ID': Machine identifier.
            - 'Record_Count': Observation count per machine.
            - 'Mean_Latency_ms': Machine mean latency.
            - 'Median_Latency_ms': Machine median latency.
            - 'Jitter_ms': Sample standard deviation of latency (ddof=1).
            - 'Jitter_Rank': Ascending rank by jitter (1 = lowest jitter).
    """
    if df.empty or latency_col not in df.columns or machine_col not in df.columns:
        return pd.DataFrame(columns=[
            "Machine_ID", "Record_Count", "Mean_Latency_ms",
            "Median_Latency_ms", "Jitter_ms", "Jitter_Rank"
        ])

    grouped = df.groupby(machine_col)[latency_col]
    counts = grouped.count()
    means = grouped.mean()
    medians = grouped.median()
    # Sample standard deviation ddof=1 (replaces NaN with 0.0 for n=1)
    stds = grouped.std(ddof=1).fillna(0.0)

    summary_df = pd.DataFrame({
        "Machine_ID": counts.index,
        "Record_Count": counts.values,
        "Mean_Latency_ms": means.values,
        "Median_Latency_ms": medians.values,
        "Jitter_ms": stds.values,
    })

    # Sort by Jitter ascending and assign rank
    summary_df = summary_df.sort_values(by="Jitter_ms", ascending=True).reset_index(drop=True)
    summary_df["Jitter_Rank"] = np.arange(1, len(summary_df) + 1)

    return summary_df


def compute_machine_network_summary(
    df: pd.DataFrame,
    machine_col: str = "Machine_ID",
    latency_col: str = "Network_Latency_ms",
    loss_col: str = "Packet_Loss_%",
) -> pd.DataFrame:
    """
    Compute comprehensive machine-level network QoS comparison statistics.

    Parameters:
        df: Input telemetry DataFrame.
        machine_col: Column name for machine identifier.
        latency_col: Column name for latency.
        loss_col: Column name for packet loss.

    Returns:
        DataFrame containing machine-level summary metrics.
    """
    if df.empty:
        return pd.DataFrame(columns=[
            "Machine_ID", "Record_Count", "Mean_Latency_ms", "Median_Latency_ms",
            "P95_Latency_ms", "Jitter_ms", "Mean_Packet_Loss_pct",
            "Median_Packet_Loss_pct", "P95_Packet_Loss_pct", "Zero_Loss_Count"
        ])

    records = []
    for m_id, grp in df.groupby(machine_col):
        lat = grp[latency_col].dropna()
        loss = grp[loss_col].dropna() if loss_col in grp.columns else pd.Series(dtype=float)

        n = len(lat)
        if n == 0:
            continue

        records.append({
            "Machine_ID": m_id,
            "Record_Count": n,
            "Mean_Latency_ms": float(lat.mean()),
            "Median_Latency_ms": float(lat.median()),
            "P95_Latency_ms": float(np.percentile(lat, 95)) if n >= 20 else float(lat.max()),
            "Jitter_ms": float(lat.std(ddof=1)) if n > 1 else 0.0,
            "Mean_Packet_Loss_pct": float(loss.mean()) if len(loss) > 0 else 0.0,
            "Median_Packet_Loss_pct": float(loss.median()) if len(loss) > 0 else 0.0,
            "P95_Packet_Loss_pct": float(np.percentile(loss, 95)) if len(loss) >= 20 else float(loss.max()) if len(loss) > 0 else 0.0,
            "Zero_Loss_Count": int((loss == 0.0).sum()) if len(loss) > 0 else 0,
        })

    res_df = pd.DataFrame(records)
    if not res_df.empty:
        res_df = res_df.sort_values(by="Machine_ID").reset_index(drop=True)
    return res_df


# ---------------------------------------------------------------------------
# 3. Multivariate Mahalanobis Distance Screening (Module 2)
# ---------------------------------------------------------------------------

def compute_mahalanobis_distances(
    df: pd.DataFrame,
    feature_cols: Optional[List[str]] = None,
    alpha: float = 0.001,
) -> Dict[str, Any]:
    """
    Compute multivariate Mahalanobis distance screening profile over sensor features.

    Mahalanobis distance squared is defined as:
        D^2 = (x - mu)^T * Sigma^{-1} * (x - mu)

    Under the baseline assumption of multivariate normality, D^2 follows a
    chi-square distribution with degrees of freedom equal to the number of
    features p: D^2 ~ chi2(p). The critical screening cutoff is chi2_{1-alpha}(p).

    CRITICAL SAFEGUARD:
    Statistical distance from the sample centroid is strictly an exploratory
    screening diagnostic. Low or zero exceedance does NOT confirm absence of
    mechanical failure, nor does an elevated score confirm physical fault.

    Parameters:
        df: Input DataFrame containing numeric feature columns.
        feature_cols: List of continuous features (default: ['Temperature_C', 'Vibration_Hz']).
        alpha: Screening significance level (default: 0.001 for 99.9% fence).

    Returns:
        Dictionary containing:
            - 'distances': 1D np.ndarray of Mahalanobis distances (D).
            - 'squared_distances': 1D np.ndarray of squared distances (D^2).
            - 'threshold': Critical threshold value for D (sqrt(chi2_cutoff)).
            - 'threshold_squared': Critical chi2 cutoff for D^2.
            - 'outlier_count': Number of observations with D > threshold.
            - 'outlier_pct': Percentage of observations exceeding threshold.
            - 'mean_distance': Sample mean Mahalanobis distance.
            - 'median_distance': Sample median Mahalanobis distance.
            - 'max_distance': Sample maximum Mahalanobis distance.
            - 'percentiles': Dict of key distance percentiles (P50, P90, P95, P99).
            - 'feature_cols': List of evaluated feature column names.
            - 'n_observations': Number of analyzed observations.
    """
    if feature_cols is None:
        feature_cols = ["Temperature_C", "Vibration_Hz"]

    empty_result: Dict[str, Any] = {
        "distances": np.array([], dtype=float),
        "squared_distances": np.array([], dtype=float),
        "threshold": 0.0,
        "threshold_squared": 0.0,
        "outlier_count": 0,
        "outlier_pct": 0.0,
        "mean_distance": 0.0,
        "median_distance": 0.0,
        "max_distance": 0.0,
        "percentiles": {"p50": 0.0, "p90": 0.0, "p95": 0.0, "p99": 0.0},
        "feature_cols": feature_cols,
        "n_observations": 0,
    }

    if df.empty:
        return empty_result

    # Check that required columns exist
    for col in feature_cols:
        if col not in df.columns:
            return empty_result

    clean_df = df[feature_cols].dropna()
    n = len(clean_df)
    p = len(feature_cols)

    # Need at least p + 1 points to estimate covariance
    if n <= p:
        return empty_result

    X = clean_df.to_numpy(dtype=float)
    mean_vec = np.mean(X, axis=0)
    diff = X - mean_vec

    cov_matrix = np.cov(X, rowvar=False)

    # Defensive pseudo-inverse in case of collinearity/near-singularity
    try:
        inv_cov = np.linalg.pinv(cov_matrix)
    except np.linalg.LinAlgError:
        return empty_result

    # Vectorized computation: D^2 = sum_j (diff @ inv_cov)_ij * diff_ij
    d_squared = np.sum((diff @ inv_cov) * diff, axis=1)
    # Numerical safeguard against tiny negative values due to floating-point rounding
    d_squared = np.maximum(d_squared, 0.0)
    distances = np.sqrt(d_squared)

    # Theoretical chi-square screening cutoff
    chi2_cutoff = float(stats.chi2.ppf(1.0 - alpha, df=p))
    dist_cutoff = float(np.sqrt(chi2_cutoff))

    outlier_mask = d_squared > chi2_cutoff
    outlier_count = int(np.sum(outlier_mask))
    outlier_pct = float((outlier_count / n) * 100.0)

    return {
        "distances": distances,
        "squared_distances": d_squared,
        "threshold": dist_cutoff,
        "threshold_squared": chi2_cutoff,
        "outlier_count": outlier_count,
        "outlier_pct": outlier_pct,
        "mean_distance": float(np.mean(distances)),
        "median_distance": float(np.median(distances)),
        "max_distance": float(np.max(distances)),
        "percentiles": {
            "p50": float(np.percentile(distances, 50)),
            "p90": float(np.percentile(distances, 90)),
            "p95": float(np.percentile(distances, 95)),
            "p99": float(np.percentile(distances, 99)),
        },
        "feature_cols": feature_cols,
        "n_observations": n,
    }


# ---------------------------------------------------------------------------
# 4. Machine Health Comparative Summary (Module 2)
# ---------------------------------------------------------------------------

def compute_machine_health_summary(
    df: pd.DataFrame,
    machine_col: str = "Machine_ID",
    temp_col: str = "Temperature_C",
    vib_col: str = "Vibration_Hz",
    pm_col: str = "Predictive_Maintenance_Score",
) -> pd.DataFrame:
    """
    Compute machine-level mechanical condition summaries across fleet units.

    Parameters:
        df: Input telemetry DataFrame.
        machine_col: Machine identifier column.
        temp_col: Temperature column.
        vib_col: Vibration column.
        pm_col: Predictive Maintenance Score column.

    Returns:
        DataFrame containing machine-level mechanical condition benchmarks.
    """
    if df.empty:
        return pd.DataFrame(columns=[
            "Machine_ID", "Record_Count", "Mean_Temperature_C",
            "Median_Temperature_C", "Mean_Vibration_Hz", "Median_Vibration_Hz",
            "Mean_PM_Score", "Median_PM_Score", "Max_Mahalanobis_D"
        ])

    records = []
    for m_id, grp in df.groupby(machine_col):
        temp = grp[temp_col].dropna() if temp_col in grp.columns else pd.Series(dtype=float)
        vib = grp[vib_col].dropna() if vib_col in grp.columns else pd.Series(dtype=float)
        pm = grp[pm_col].dropna() if pm_col in grp.columns else pd.Series(dtype=float)

        n = len(grp)
        if n == 0:
            continue

        # Compute machine-level Mahalanobis max if features present
        max_d = 0.0
        if len(temp) > 2 and len(vib) > 2:
            m_res = compute_mahalanobis_distances(grp[[temp_col, vib_col]])
            max_d = m_res.get("max_distance", 0.0)

        records.append({
            "Machine_ID": m_id,
            "Record_Count": n,
            "Mean_Temperature_C": float(temp.mean()) if len(temp) > 0 else 0.0,
            "Median_Temperature_C": float(temp.median()) if len(temp) > 0 else 0.0,
            "Mean_Vibration_Hz": float(vib.mean()) if len(vib) > 0 else 0.0,
            "Median_Vibration_Hz": float(vib.median()) if len(vib) > 0 else 0.0,
            "Mean_PM_Score": float(pm.mean()) if len(pm) > 0 else 0.0,
            "Median_PM_Score": float(pm.median()) if len(pm) > 0 else 0.0,
            "Max_Mahalanobis_D": max_d,
        })

    res_df = pd.DataFrame(records)
    if not res_df.empty:
        res_df = res_df.sort_values(by="Machine_ID").reset_index(drop=True)
    return res_df


# ---------------------------------------------------------------------------
# 5. Production & Energy Analytics (Module 3)
# ---------------------------------------------------------------------------

def compute_production_energy_summary(
    df: pd.DataFrame,
    machine_col: str = "Machine_ID",
    speed_col: str = "Production_Speed_units_per_hr",
    power_col: str = "Power_Consumption_kW",
) -> pd.DataFrame:
    """
    Compute machine-level production speed, power demand, and SEC summary metrics.

    Specific Energy Consumption (SEC) is evaluated strictly at row level for
    observations where production speed is strictly positive (> 0):
        SEC = power divided by production speed (kWh/unit)

    Parameters:
        df: Input DataFrame.
        machine_col: Column name for machine identifier.
        speed_col: Column name for production speed (units/hr).
        power_col: Column name for power consumption (kW).

    Returns:
        DataFrame containing machine-level throughput, power, and SEC statistics.
    """
    expected_cols = [
        "Machine_ID", "Record_Count", "Mean_Speed_u_per_hr", "Median_Speed_u_per_hr",
        "Std_Speed_u_per_hr", "Min_Speed_u_per_hr", "Max_Speed_u_per_hr",
        "Mean_Power_kW", "Median_Power_kW", "Std_Power_kW", "Min_Power_kW",
        "Max_Power_kW", "Mean_SEC_kWh_per_u", "Median_SEC_kWh_per_u",
        "Speed_Rank", "Power_Rank", "SEC_Rank"
    ]
    if df.empty or machine_col not in df.columns:
        return pd.DataFrame(columns=expected_cols)

    records = []
    for m_id, grp in df.groupby(machine_col):
        n = len(grp)
        if n == 0:
            continue

        sp = grp[speed_col].dropna() if speed_col in grp.columns else pd.Series(dtype=float)
        pw = grp[power_col].dropna() if power_col in grp.columns else pd.Series(dtype=float)

        # SEC row-level calculation with strict positive speed guard
        if speed_col in grp.columns and power_col in grp.columns:
            pos_mask = (grp[speed_col] > 0) & (~grp[speed_col].isna()) & (~grp[power_col].isna())
            if pos_mask.sum() > 0:
                sec_series = grp.loc[pos_mask, power_col] / grp.loc[pos_mask, speed_col]
                mean_sec = float(sec_series.mean())
                med_sec = float(sec_series.median())
            else:
                mean_sec = 0.0
                med_sec = 0.0
        else:
            mean_sec = 0.0
            med_sec = 0.0

        records.append({
            "Machine_ID": m_id,
            "Record_Count": n,
            "Mean_Speed_u_per_hr": float(sp.mean()) if len(sp) > 0 else 0.0,
            "Median_Speed_u_per_hr": float(sp.median()) if len(sp) > 0 else 0.0,
            "Std_Speed_u_per_hr": float(sp.std(ddof=1)) if len(sp) > 1 else 0.0,
            "Min_Speed_u_per_hr": float(sp.min()) if len(sp) > 0 else 0.0,
            "Max_Speed_u_per_hr": float(sp.max()) if len(sp) > 0 else 0.0,
            "Mean_Power_kW": float(pw.mean()) if len(pw) > 0 else 0.0,
            "Median_Power_kW": float(pw.median()) if len(pw) > 0 else 0.0,
            "Std_Power_kW": float(pw.std(ddof=1)) if len(pw) > 1 else 0.0,
            "Min_Power_kW": float(pw.min()) if len(pw) > 0 else 0.0,
            "Max_Power_kW": float(pw.max()) if len(pw) > 0 else 0.0,
            "Mean_SEC_kWh_per_u": mean_sec,
            "Median_SEC_kWh_per_u": med_sec,
        })

    res_df = pd.DataFrame(records)
    if res_df.empty:
        return pd.DataFrame(columns=expected_cols)

    # Assign competitive rankings
    res_df["Speed_Rank"] = res_df["Mean_Speed_u_per_hr"].rank(ascending=False, method="min").astype(int)
    res_df["Power_Rank"] = res_df["Mean_Power_kW"].rank(ascending=True, method="min").astype(int)
    res_df["SEC_Rank"] = res_df["Mean_SEC_kWh_per_u"].rank(ascending=True, method="min").astype(int)

    return res_df.sort_values(by="Machine_ID").reset_index(drop=True)


def compute_temporal_daily_summary(
    df: pd.DataFrame,
    date_col: str = "Date",
    speed_col: str = "Production_Speed_units_per_hr",
    power_col: str = "Power_Consumption_kW",
    defect_col: str = "Quality_Control_Defect_Rate_%",
    error_col: str = "Error_Rate_%",
) -> pd.DataFrame:
    """
    Compute daily chronological aggregate metrics across all calendar dates.

    Parameters:
        df: Input DataFrame containing date and metric columns.
        date_col: Column name containing date strings (DD-MM-YYYY).
        speed_col: Column name for production speed.
        power_col: Column name for power consumption.
        defect_col: Column name for defect rate.
        error_col: Column name for process error rate.

    Returns:
        DataFrame sorted chronologically by parsed calendar date.
    """
    expected_cols = [
        "Date", "parsed_date", "Record_Count", "Mean_Speed_u_per_hr",
        "Mean_Power_kW", "Mean_SEC_kWh_per_u", "Mean_Defect_Rate_pct",
        "Mean_Error_Rate_pct", "Arithmetic_Complement_pct"
    ]
    if df.empty or date_col not in df.columns:
        return pd.DataFrame(columns=expected_cols)

    records = []
    for d_val, grp in df.groupby(date_col):
        n = len(grp)
        if n == 0:
            continue

        sp = grp[speed_col].dropna() if speed_col in grp.columns else pd.Series(dtype=float)
        pw = grp[power_col].dropna() if power_col in grp.columns else pd.Series(dtype=float)
        dfc = grp[defect_col].dropna() if defect_col in grp.columns else pd.Series(dtype=float)
        err = grp[error_col].dropna() if error_col in grp.columns else pd.Series(dtype=float)

        # Row-level SEC for positive speed records
        if speed_col in grp.columns and power_col in grp.columns:
            pos_mask = (grp[speed_col] > 0) & (~grp[speed_col].isna()) & (~grp[power_col].isna())
            mean_sec = float((grp.loc[pos_mask, power_col] / grp.loc[pos_mask, speed_col]).mean()) if pos_mask.sum() > 0 else 0.0
        else:
            mean_sec = 0.0

        mean_dfc = float(dfc.mean()) if len(dfc) > 0 else 0.0
        arith_comp = 100.0 - mean_dfc if len(dfc) > 0 else 100.0

        records.append({
            "Date": str(d_val),
            "Record_Count": n,
            "Mean_Speed_u_per_hr": float(sp.mean()) if len(sp) > 0 else 0.0,
            "Mean_Power_kW": float(pw.mean()) if len(pw) > 0 else 0.0,
            "Mean_SEC_kWh_per_u": mean_sec,
            "Mean_Defect_Rate_pct": mean_dfc,
            "Mean_Error_Rate_pct": float(err.mean()) if len(err) > 0 else 0.0,
            "Arithmetic_Complement_pct": arith_comp,
        })

    res_df = pd.DataFrame(records)
    if res_df.empty:
        return pd.DataFrame(columns=expected_cols)

    # Parse dates safely to ensure chronological ordering
    try:
        res_df["parsed_date"] = pd.to_datetime(res_df["Date"], format="%d-%m-%Y")
    except Exception:
        res_df["parsed_date"] = pd.to_datetime(res_df["Date"], errors="coerce")

    return res_df.sort_values(by="parsed_date").reset_index(drop=True)


def compute_mode_stratified_summary(
    df: pd.DataFrame,
    mode_col: str = "Operation_Mode",
    speed_col: str = "Production_Speed_units_per_hr",
    power_col: str = "Power_Consumption_kW",
    defect_col: str = "Quality_Control_Defect_Rate_%",
    error_col: str = "Error_Rate_%",
) -> pd.DataFrame:
    """
    Compute operational mode comparisons across production, power, SEC, and quality.

    Parameters:
        df: Input DataFrame.
        mode_col: Column name for operation mode.
        speed_col: Column name for production speed.
        power_col: Column name for power consumption.
        defect_col: Column name for defect rate.
        error_col: Column name for error rate.

    Returns:
        DataFrame detailing descriptive metrics for each operation mode.
    """
    expected_cols = [
        "Operation_Mode", "Record_Count", "Record_Pct", "Mean_Speed_u_per_hr",
        "Std_Speed_u_per_hr", "Mean_Power_kW", "Std_Power_kW", "Mean_SEC_kWh_per_u",
        "Mean_Defect_Rate_pct", "Mean_Error_Rate_pct"
    ]
    if df.empty or mode_col not in df.columns:
        return pd.DataFrame(columns=expected_cols)

    total_n = len(df)
    records = []
    # Guarantee canonical mode ordering
    canonical_modes = ["Active", "Idle", "Maintenance"]
    present_modes = [m for m in canonical_modes if m in df[mode_col].values]
    # Add any extra observed modes if present
    for m in df[mode_col].unique():
        if m not in present_modes and pd.notna(m):
            present_modes.append(m)

    for mode in present_modes:
        grp = df[df[mode_col] == mode]
        n = len(grp)
        if n == 0:
            continue

        sp = grp[speed_col].dropna() if speed_col in grp.columns else pd.Series(dtype=float)
        pw = grp[power_col].dropna() if power_col in grp.columns else pd.Series(dtype=float)
        dfc = grp[defect_col].dropna() if defect_col in grp.columns else pd.Series(dtype=float)
        err = grp[error_col].dropna() if error_col in grp.columns else pd.Series(dtype=float)

        if speed_col in grp.columns and power_col in grp.columns:
            pos_mask = (grp[speed_col] > 0) & (~grp[speed_col].isna()) & (~grp[power_col].isna())
            mean_sec = float((grp.loc[pos_mask, power_col] / grp.loc[pos_mask, speed_col]).mean()) if pos_mask.sum() > 0 else 0.0
        else:
            mean_sec = 0.0

        records.append({
            "Operation_Mode": mode,
            "Record_Count": n,
            "Record_Pct": float((n / total_n) * 100.0) if total_n > 0 else 0.0,
            "Mean_Speed_u_per_hr": float(sp.mean()) if len(sp) > 0 else 0.0,
            "Std_Speed_u_per_hr": float(sp.std(ddof=1)) if len(sp) > 1 else 0.0,
            "Mean_Power_kW": float(pw.mean()) if len(pw) > 0 else 0.0,
            "Std_Power_kW": float(pw.std(ddof=1)) if len(pw) > 1 else 0.0,
            "Mean_SEC_kWh_per_u": mean_sec,
            "Mean_Defect_Rate_pct": float(dfc.mean()) if len(dfc) > 0 else 0.0,
            "Mean_Error_Rate_pct": float(err.mean()) if len(err) > 0 else 0.0,
        })

    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# 6. Quality & Process Efficiency Analytics (Module 4)
# ---------------------------------------------------------------------------

def compute_quality_machine_summary(
    df: pd.DataFrame,
    machine_col: str = "Machine_ID",
    defect_col: str = "Quality_Control_Defect_Rate_%",
    error_col: str = "Error_Rate_%",
) -> pd.DataFrame:
    """
    Compute machine-level finished-good defect rates and process error metrics.

    Parameters:
        df: Input DataFrame.
        machine_col: Column name for machine identifier.
        defect_col: Column name for defect rate (%).
        error_col: Column name for process error rate (%).

    Returns:
        DataFrame containing machine quality statistics and rankings.
    """
    expected_cols = [
        "Machine_ID", "Record_Count", "Mean_Defect_Rate_pct", "Median_Defect_Rate_pct",
        "Std_Defect_Rate_pct", "Min_Defect_Rate_pct", "Max_Defect_Rate_pct",
        "Arithmetic_Complement_pct", "Mean_Error_Rate_pct", "Median_Error_Rate_pct",
        "Std_Error_Rate_pct", "Defect_Rank", "Error_Rank"
    ]
    if df.empty or machine_col not in df.columns:
        return pd.DataFrame(columns=expected_cols)

    records = []
    for m_id, grp in df.groupby(machine_col):
        n = len(grp)
        if n == 0:
            continue

        dfc = grp[defect_col].dropna() if defect_col in grp.columns else pd.Series(dtype=float)
        err = grp[error_col].dropna() if error_col in grp.columns else pd.Series(dtype=float)

        mean_dfc = float(dfc.mean()) if len(dfc) > 0 else 0.0
        arith_comp = 100.0 - mean_dfc if len(dfc) > 0 else 100.0

        records.append({
            "Machine_ID": m_id,
            "Record_Count": n,
            "Mean_Defect_Rate_pct": mean_dfc,
            "Median_Defect_Rate_pct": float(dfc.median()) if len(dfc) > 0 else 0.0,
            "Std_Defect_Rate_pct": float(dfc.std(ddof=1)) if len(dfc) > 1 else 0.0,
            "Min_Defect_Rate_pct": float(dfc.min()) if len(dfc) > 0 else 0.0,
            "Max_Defect_Rate_pct": float(dfc.max()) if len(dfc) > 0 else 0.0,
            "Arithmetic_Complement_pct": arith_comp,
            "Mean_Error_Rate_pct": float(err.mean()) if len(err) > 0 else 0.0,
            "Median_Error_Rate_pct": float(err.median()) if len(err) > 0 else 0.0,
            "Std_Error_Rate_pct": float(err.std(ddof=1)) if len(err) > 1 else 0.0,
        })

    res_df = pd.DataFrame(records)
    if res_df.empty:
        return pd.DataFrame(columns=expected_cols)

    # Assign competitive rankings (lower defect rate = better rank)
    res_df["Defect_Rank"] = res_df["Mean_Defect_Rate_pct"].rank(ascending=True, method="min").astype(int)
    res_df["Error_Rank"] = res_df["Mean_Error_Rate_pct"].rank(ascending=True, method="min").astype(int)

    return res_df.sort_values(by="Machine_ID").reset_index(drop=True)


def compute_efficiency_contingency(
    df: pd.DataFrame,
    row_col: str = "Operation_Mode",
    status_col: str = "Efficiency_Status",
) -> pd.DataFrame:
    """
    Compute cross-tabulation of Efficiency_Status tiers across operation modes or machine units.

    Parameters:
        df: Input DataFrame.
        row_col: Grouping dimension (default: 'Operation_Mode').
        status_col: Classification column (default: 'Efficiency_Status').

    Returns:
        DataFrame cross-tabulation with counts and row percentages.
    """
    expected_cols = [
        row_col, "Total_Count", "Low_Count", "Medium_Count", "High_Count",
        "Low_Pct", "Medium_Pct", "High_Pct"
    ]
    if df.empty or row_col not in df.columns or status_col not in df.columns:
        return pd.DataFrame(columns=expected_cols)

    ct = pd.crosstab(df[row_col], df[status_col])
    records = []
    for r_val in ct.index:
        low_c = int(ct.loc[r_val, "Low"]) if "Low" in ct.columns else 0
        med_c = int(ct.loc[r_val, "Medium"]) if "Medium" in ct.columns else 0
        high_c = int(ct.loc[r_val, "High"]) if "High" in ct.columns else 0
        total_c = low_c + med_c + high_c

        records.append({
            row_col: r_val,
            "Total_Count": total_c,
            "Low_Count": low_c,
            "Medium_Count": med_c,
            "High_Count": high_c,
            "Low_Pct": (low_c / total_c * 100.0) if total_c > 0 else 0.0,
            "Medium_Pct": (med_c / total_c * 100.0) if total_c > 0 else 0.0,
            "High_Pct": (high_c / total_c * 100.0) if total_c > 0 else 0.0,
        })

    return pd.DataFrame(records)


