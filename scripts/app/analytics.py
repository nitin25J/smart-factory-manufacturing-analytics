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

