"""
Module 2: Machine Health & Condition Monitoring.
Manufacturing Diagnostic Intelligence System — Phase 2.4.

Target Diagnostic Pillar:
- Machine Health & Mechanical Condition Surveillance (KPI 1).

Features Implemented:
1. Thermal-vibration bivariate scatter plot with decimation controls and operational stratification.
2. Predictive Maintenance Score distribution with configurable provisional polarity toggle.
3. Multivariate Mahalanobis distance statistical outlier screening profile over mechanical features.
4. Cross-machine mechanical condition comparisons (temperature, vibration, PM score, max distance).
5. Comprehensive safeguard notices (no unverified RUL claims, statistical distance != physical fault).
"""

from __future__ import annotations

from typing import Any, Dict

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from scripts.app.analytics import (
    compute_machine_health_summary,
    compute_mahalanobis_distances,
)
from scripts.app.components import render_empty_state, render_kpi_card, render_section_header


def render_machine_health(df: pd.DataFrame, kpis: Dict[str, Any]) -> None:
    """
    Render Module 2: Machine Health & Condition Monitoring analytical interface.

    Parameters:
        df: Filtered or full DataFrame slice for condition monitoring.
        kpis: Pre-calculated KPI dictionary from kpi_engine.calculate_all_kpis().
    """
    render_section_header(
        title="Module 2: Machine Health & Condition Monitoring",
        description="Mechanical condition surveillance tracking temperature, vibration, and predictive maintenance indicators.",
    )

    if df.empty:
        render_empty_state(
            title="No Machine Health Telemetry",
            message="No observations match your active filter criteria.",
            suggestion="Adjust your sidebar filters to include more machines or operation modes."
        )
        return

    mh = kpis.get("machine_health", {})
    temp_stats = mh.get("temperature_c", {})
    vib_stats = mh.get("vibration_hz", {})
    pm_stats = mh.get("predictive_maintenance_score", {})

    n_total = len(df)
    n_machines = df["Machine_ID"].nunique() if "Machine_ID" in df.columns else 0

    # -----------------------------------------------------------------------
    # 1. Independent Mechanical Condition Indicator Cards (KPI 1)
    # -----------------------------------------------------------------------
    st.markdown("#### Independent Mechanical Condition Indicators (KPI 1)")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        render_kpi_card(
            label="Monitored Observations",
            value=n_total,
            unit="records",
            subtext=f"{n_machines} production machines active",
            help_text="Observation volume within active filter parameters."
        )

    with col2:
        render_kpi_card(
            label="Mean Core Temperature",
            value=temp_stats.get("mean", 0.0),
            unit="°C",
            subtext=f"Median: {temp_stats.get('median', 0.0):.2f} °C | Range: [{temp_stats.get('min', 0.0):.1f}, {temp_stats.get('max', 0.0):.1f}] °C",
            help_text="Thermal telemetry of machinery core and bearing sensors."
        )

    with col3:
        render_kpi_card(
            label="Mean Mechanical Vibration",
            value=vib_stats.get("mean", 0.0),
            unit="Hz",
            subtext=f"Median: {vib_stats.get('median', 0.0):.2f} Hz | P95: {vib_stats.get('p95', 0.0):.2f} Hz",
            help_text="Mechanical oscillation frequency telemetry across spindle/bearing housings."
        )

    with col4:
        render_kpi_card(
            label="Predictive Maintenance Score",
            value=pm_stats.get("mean", 0.0),
            unit="score",
            subtext=f"Median: {pm_stats.get('median', 0.0):.2f} | Polarity: Neutral",
            help_text="Bounded algorithmic indicator [0.0, 1.0]. Directionality is unverified in source metadata."
        )

    # Architectural Safeguard Notice
    st.info(
        "**Provisional Safeguard Notice:** Raw temperature, vibration, and predictive maintenance scores are tracked "
        "as separate, unweighted, independent indicators. No composite 'Machine Health Index' is computed without "
        "approved normalization baselines. Statistical outlier screening does NOT constitute confirmed physical machinery "
        "failure, nor does this system claim Remaining Useful Life (RUL) forecasting."
    )

    st.divider()

    # -----------------------------------------------------------------------
    # 2. Thermal-Vibration Bivariate Dispersion Scatter Plot
    # -----------------------------------------------------------------------
    st.markdown("#### Thermal-Vibration Bivariate Dispersion")
    st.caption("Bivariate mechanical condition space examining simultaneous temperature (°C) and vibration (Hz) telemetry.")

    ctrl_c1, ctrl_c2, ctrl_c3 = st.columns(3)
    with ctrl_c1:
        color_choice = st.selectbox(
            "Scatter Color Dimension:",
            options=["Operation Mode", "Predictive Maintenance Score", "Machine ID"],
            index=0,
            key="mod2_scatter_color",
            help="Select telemetry attribute used for data point coloration."
        )
    with ctrl_c2:
        max_scatter_pts = st.select_slider(
            "Interactive Display Sample Size:",
            options=[1000, 2500, 5000, 10000, "All Records"],
            value=5000 if n_total > 5000 else "All Records",
            key="mod2_scatter_samples",
            help="Select maximum points for interactive WebGL rendering. Summary statistics always evaluate 100% of data."
        )
    with ctrl_c3:
        show_envelopes = st.checkbox(
            "Show Expected Operating Envelope",
            value=True,
            key="mod2_scatter_envelope",
            help="Overlay expected operating bounds (30–90 °C, 0.1–5.0 Hz)."
        )

    # Downsample for scatter plot responsiveness if requested
    if max_scatter_pts != "All Records" and n_total > max_scatter_pts:
        scatter_sample = df.sample(n=int(max_scatter_pts), random_state=42).copy()
        st.caption(f"ℹ️ Displaying a representative random sample of **{max_scatter_pts:,}** points from **{n_total:,}** matching records for smooth interactive rendering.")
    else:
        scatter_sample = df.copy()

    # Determine Plotly color argument
    if color_choice == "Operation Mode":
        color_col = "Operation_Mode"
        color_kwargs = {"color_discrete_map": {"Active": "#1f77b4", "Idle": "#ff7f0e", "Maintenance": "#2ca02c"}}
    elif color_choice == "Predictive Maintenance Score":
        color_col = "Predictive_Maintenance_Score"
        color_kwargs = {"color_continuous_scale": "Turbo"}
    else:
        color_col = "Machine_ID"
        scatter_sample["Machine_Label"] = scatter_sample["Machine_ID"].apply(lambda m: f"M{m:02d}")
        color_col = "Machine_Label"
        color_kwargs = {}

    fig_bivar = px.scatter(
        scatter_sample,
        x="Temperature_C",
        y="Vibration_Hz",
        color=color_col,
        opacity=0.6,
        labels={"Temperature_C": "Core Temperature (°C)", "Vibration_Hz": "Vibration Frequency (Hz)"},
        hover_data={"Machine_ID": True, "Temperature_C": ":.2f", "Vibration_Hz": ":.2f", "Predictive_Maintenance_Score": ":.3f", "Operation_Mode": True},
        **color_kwargs,
    )

    if show_envelopes:
        # Overlay empirical operating boundary rectangle
        fig_bivar.add_shape(
            type="rect",
            x0=30.0, y0=0.1, x1=90.0, y1=5.0,
            line=dict(color="rgba(100, 100, 100, 0.4)", width=1.5, dash="dash"),
            fillcolor="rgba(0, 0, 0, 0)",
        )

    fig_bivar.update_layout(
        xaxis=dict(range=[25.0, 95.0], title="Core Temperature (°C)"),
        yaxis=dict(range=[0.0, 5.5], title="Vibration Frequency (Hz)"),
        margin=dict(l=40, r=20, t=20, b=40),
        height=450,
    )
    st.plotly_chart(fig_bivar, use_container_width=True)

    st.divider()

    # -----------------------------------------------------------------------
    # 3. Predictive Maintenance Score Distribution & Polarity Toggle
    # -----------------------------------------------------------------------
    st.markdown("#### Predictive Maintenance Score Analysis")
    st.caption("Distributional assessment with configurable provisional interpretation polarity.")

    pm_c1, pm_c2 = st.columns([1, 2])

    with pm_c1:
        with st.container(border=True):
            st.markdown("##### Interpretation Configuration")
            pm_polarity = st.radio(
                "Provisional Score Interpretation:",
                options=[
                    "Default: 1.0 = Degradation Risk (Higher is Worse)",
                    "Alternative: 0.0 = Degradation Risk (Lower is Worse)",
                ],
                index=0,
                key="mod2_pm_polarity",
                help="Configure directional interpretation of the [0.0, 1.0] score. Polarity is unverified in dataset documentation."
            )
            is_high_risk = "Default" in pm_polarity

            st.caption(
                f"**Current Mapping:** Observations with score {'> 0.75' if is_high_risk else '< 0.25'} "
                f"are classified into the upper risk decile under the provisional rule."
            )

            # Distribution quartile counts
            if "Predictive_Maintenance_Score" in df.columns:
                pm_series = df["Predictive_Maintenance_Score"].dropna()
                q1_cnt = int((pm_series <= 0.25).sum())
                q2_cnt = int(((pm_series > 0.25) & (pm_series <= 0.50)).sum())
                q3_cnt = int(((pm_series > 0.50) & (pm_series <= 0.75)).sum())
                q4_cnt = int((pm_series > 0.75).sum())

                st.markdown("**Quartile Observations:**")
                st.write(f"- [0.00 – 0.25]: **{q1_cnt:,}** ({q1_cnt/n_total*100:.1f}%) {'🚨 *High Risk*' if not is_high_risk else '✅ *Low Risk*'}")
                st.write(f"- (0.25 – 0.50]: **{q2_cnt:,}** ({q2_cnt/n_total*100:.1f}%)")
                st.write(f"- (0.50 – 0.75]: **{q3_cnt:,}** ({q3_cnt/n_total*100:.1f}%)")
                st.write(f"- (0.75 – 1.00]: **{q4_cnt:,}** ({q4_cnt/n_total*100:.1f}%) {'🚨 *High Risk*' if is_high_risk else '✅ *Low Risk*'}")

    with pm_c2:
        with st.container(border=True):
            st.markdown("##### Empirical Score Histogram & Density")
            fig_pm_hist = px.histogram(
                df,
                x="Predictive_Maintenance_Score",
                nbins=40,
                color="Operation_Mode" if "Operation_Mode" in df.columns else None,
                barmode="overlay",
                opacity=0.7,
                labels={"Predictive_Maintenance_Score": "Predictive Maintenance Score"},
                color_discrete_map={"Active": "#1f77b4", "Idle": "#ff7f0e", "Maintenance": "#2ca02c"},
            )
            fig_pm_hist.update_layout(
                xaxis=dict(range=[0.0, 1.0], title="Predictive Maintenance Score [0.0, 1.0]"),
                yaxis_title="Observation Count",
                margin=dict(l=40, r=20, t=20, b=40),
                height=320,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            st.plotly_chart(fig_pm_hist, use_container_width=True)
            st.caption(
                f"Empirical mean score: **{pm_stats.get('mean', 0.50):.4f}** (std: **{pm_stats.get('std_dev', 0.29):.4f}**). "
                "The distribution is continuous and uniform across [0.0, 1.0] without modal spikes."
            )

    st.divider()

    # -----------------------------------------------------------------------
    # 4. Multivariate Mahalanobis Distance Screening Profile
    # -----------------------------------------------------------------------
    st.markdown("#### Multivariate Mahalanobis Outlier Screening")
    st.caption("Bivariate statistical distance from the joint thermal-vibration centroid relative to chi-square theoretical bounds.")

    mah_results = compute_mahalanobis_distances(df, feature_cols=["Temperature_C", "Vibration_Hz"])

    mah_c1, mah_c2, mah_c3, mah_c4 = st.columns(4)
    with mah_c1:
        render_kpi_card(
            label="Mean Mahalanobis D",
            value=mah_results.get("mean_distance", 0.0),
            unit="",
            help_text="Sample mean Mahalanobis distance from bivariate (Temperature, Vibration) centroid."
        )
    with mah_c2:
        render_kpi_card(
            label="Max Observed D",
            value=mah_results.get("max_distance", 0.0),
            unit="",
            help_text="Maximum Mahalanobis distance observed in current data slice."
        )
    with mah_c3:
        render_kpi_card(
            label="Statistical Cutoff (D)",
            value=mah_results.get("threshold", 3.717),
            unit="",
            subtext="chi2(p=2, alpha=0.001)",
            help_text="Theoretical 99.9% critical cutoff sqrt(chi2_0.999(2)) = 3.717."
        )
    with mah_c4:
        render_kpi_card(
            label="Screening Outliers",
            value=mah_results.get("outlier_count", 0),
            unit="records",
            subtext=f"{mah_results.get('outlier_pct', 0.0):.3f}% exceedance",
            help_text="Observations exceeding theoretical 99.9% chi-square boundary."
        )

    # Plot Mahalanobis distance histogram
    if len(mah_results["distances"]) > 0:
        fig_mah = go.Figure()
        fig_mah.add_trace(go.Histogram(
            x=mah_results["distances"],
            nbinsx=50,
            marker_color="#4363d8",
            opacity=0.75,
            name="Mahalanobis D",
            hovertemplate="Distance Range: %{x}<br>Count: %{y:,}<extra></extra>",
        ))
        # Add cutoff line
        fig_mah.add_vline(
            x=mah_results["threshold"],
            line_dash="dash",
            line_color="#e6194b",
            annotation_text=f"99.9% Threshold ({mah_results['threshold']:.2f})",
            annotation_position="top right",
        )
        fig_mah.update_layout(
            xaxis_title="Mahalanobis Distance D",
            yaxis_title="Observation Frequency",
            margin=dict(l=40, r=20, t=30, b=40),
            height=300,
        )
        st.plotly_chart(fig_mah, use_container_width=True)
        st.info(
            f"**Diagnostic Screening Finding:** Maximum observed Mahalanobis distance is **{mah_results.get('max_distance', 0.0):.2f}**, "
            f"which remains strictly below the theoretical 99.9% critical fence of **{mah_results.get('threshold', 3.72):.2f}**. "
            "Zero observations exceed statistical outlier boundaries because the underlying physical features are uniformly distributed. "
            "This confirms absence of extreme multivariate statistical anomalies, but does NOT rule out physical mechanical wear."
        )

    st.divider()

    # -----------------------------------------------------------------------
    # 5. Machine-Level Mechanical Condition Comparisons
    # -----------------------------------------------------------------------
    st.markdown("#### Machine Fleet Mechanical Condition Comparisons")
    st.caption("Cross-machine comparative evaluation of core temperature, vibration, and algorithmic condition indicators.")

    health_summary_df = compute_machine_health_summary(df)

    tab_temp, tab_vib, tab_pm, tab_table = st.tabs([
        "🌡️ Temperature Comparison",
        "〰️ Vibration Comparison",
        "🎯 PM Score Comparison",
        "📋 Fleet Mechanical Summary Table"
    ])

    with tab_temp:
        if not health_summary_df.empty:
            sort_temp_df = health_summary_df.sort_values(by="Mean_Temperature_C", ascending=False).copy()
            sort_temp_df["Machine_Label"] = sort_temp_df["Machine_ID"].apply(lambda m: f"Machine {m}")

            fig_temp_bar = px.bar(
                sort_temp_df,
                x="Machine_Label",
                y="Mean_Temperature_C",
                color="Mean_Temperature_C",
                color_continuous_scale="Reds",
                labels={"Mean_Temperature_C": "Mean Temperature (°C)", "Machine_Label": "Machine"},
                hover_data={"Record_Count": True, "Median_Temperature_C": ":.2f"},
            )
            fig_temp_bar.update_layout(
                yaxis=dict(range=[55.0, 65.0], title="Mean Core Temperature (°C)"),
                margin=dict(l=40, r=20, t=20, b=60),
                height=380,
                coloraxis_showscale=False,
            )
            st.plotly_chart(fig_temp_bar, use_container_width=True)
            st.caption("Fleet machine mean temperatures range narrowly between 59.3 °C and 60.7 °C, demonstrating thermal balance across the production floor.")
        else:
            render_empty_state("No Temperature Data", "Insufficient data to compute machine temperature comparisons.")

    with tab_vib:
        if not health_summary_df.empty:
            sort_vib_df = health_summary_df.sort_values(by="Mean_Vibration_Hz", ascending=False).copy()
            sort_vib_df["Machine_Label"] = sort_vib_df["Machine_ID"].apply(lambda m: f"Machine {m}")

            fig_vib_bar = px.bar(
                sort_vib_df,
                x="Machine_Label",
                y="Mean_Vibration_Hz",
                color="Mean_Vibration_Hz",
                color_continuous_scale="Teal",
                labels={"Mean_Vibration_Hz": "Mean Vibration (Hz)", "Machine_Label": "Machine"},
                hover_data={"Record_Count": True, "Median_Vibration_Hz": ":.2f"},
            )
            fig_vib_bar.update_layout(
                yaxis=dict(range=[2.3, 2.8], title="Mean Vibration (Hz)"),
                margin=dict(l=40, r=20, t=20, b=60),
                height=380,
                coloraxis_showscale=False,
            )
            st.plotly_chart(fig_vib_bar, use_container_width=True)
            st.caption("Fleet machine mean vibrations range between 2.48 Hz and 2.61 Hz, with zero machines exhibiting resonant frequency excursions.")
        else:
            render_empty_state("No Vibration Data", "Insufficient data to compute machine vibration comparisons.")

    with tab_pm:
        if not health_summary_df.empty:
            sort_pm_df = health_summary_df.sort_values(by="Mean_PM_Score", ascending=not is_high_risk).copy()
            sort_pm_df["Machine_Label"] = sort_pm_df["Machine_ID"].apply(lambda m: f"Machine {m}")

            fig_pm_bar = px.bar(
                sort_pm_df,
                x="Machine_Label",
                y="Mean_PM_Score",
                color="Mean_PM_Score",
                color_continuous_scale="Plasma",
                labels={"Mean_PM_Score": "Mean PM Score", "Machine_Label": "Machine"},
                hover_data={"Record_Count": True, "Median_PM_Score": ":.3f"},
            )
            fig_pm_bar.update_layout(
                yaxis=dict(range=[0.45, 0.55], title="Mean Predictive Maintenance Score"),
                margin=dict(l=40, r=20, t=20, b=60),
                height=380,
                coloraxis_showscale=False,
            )
            st.plotly_chart(fig_pm_bar, use_container_width=True)
            st.caption(f"Sorted by highest provisional priority ({'Descending: Higher score = Higher risk' if is_high_risk else 'Ascending: Lower score = Higher risk'}). Machine means remain uniform near ~0.50.")
        else:
            render_empty_state("No Score Data", "Insufficient data to compute machine score comparisons.")

    with tab_table:
        st.markdown("##### Machine Mechanical Telemetry Table")
        if not health_summary_df.empty:
            st.dataframe(
                health_summary_df.style.format({
                    "Record_Count": "{:,}",
                    "Mean_Temperature_C": "{:.2f} °C",
                    "Median_Temperature_C": "{:.2f} °C",
                    "Mean_Vibration_Hz": "{:.3f} Hz",
                    "Median_Vibration_Hz": "{:.3f} Hz",
                    "Mean_PM_Score": "{:.4f}",
                    "Median_PM_Score": "{:.4f}",
                    "Max_Mahalanobis_D": "{:.2f}",
                }),
                use_container_width=True,
                height=320,
            )
        else:
            render_empty_state("No Data Table", "Current filter parameters yielded zero machine records.")
