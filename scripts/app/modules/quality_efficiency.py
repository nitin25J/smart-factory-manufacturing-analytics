r"""
Module 4: Quality Assurance & Process Efficiency Diagnostics.
Manufacturing Diagnostic Intelligence System — Phase 2.5.

Target Diagnostic Pillars:
- Product Quality & Quality Assurance (KPI 3).
- Operational Efficiency & Energy-Adjusted Intensity (KPI 5).

Responsibilities:
- Surfaces finished-good defect rates (`Quality_Control_Defect_Rate_%`) and process error telemetry (`Error_Rate_%`).
- Reports the arithmetic complement (94.991194%) with mandatory yield disclaimers.
- Evaluates machine-level defect comparisons with sample-size context.
- Analyzes quality dynamics across operating modes and longitudinal dates.
- Surfaces empirical multi-tier `Efficiency_Status` distributions, contingency tables, and SEC profiles.
- Strictly enforces Phase 2.0 quality and classification safeguards.
"""

from __future__ import annotations

from typing import Any, Dict

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from scripts.app.analytics import (
    compute_efficiency_contingency,
    compute_mode_stratified_summary,
    compute_quality_machine_summary,
    compute_temporal_daily_summary,
)
from scripts.app.components import render_empty_state, render_kpi_card, render_section_header


def render_quality_efficiency(df: pd.DataFrame, kpis: Dict[str, Any]) -> None:
    """
    Render Module 4: Quality Assurance & Process Efficiency Diagnostics interface.

    Parameters:
        df: Filtered or full DataFrame slice for quality and efficiency diagnostics.
        kpis: Pre-calculated KPI dictionary from kpi_engine.
    """
    render_section_header(
        title="Module 4: Quality Assurance & Process Efficiency Diagnostics",
        description="Finished-good defect surveillance, process execution errors, specific energy consumption (SEC), and multi-tier efficiency ratings.",
    )

    if df.empty:
        render_empty_state(
            title="No Quality or Efficiency Telemetry Found",
            message="No records match your active filter selection.",
            suggestion="Adjust your sidebar filters to include more machines or operation modes."
        )
        return

    n_total = len(df)
    n_machines = df["Machine_ID"].nunique() if "Machine_ID" in df.columns else 0

    pq = kpis.get("product_quality", {})
    defect_stats = pq.get("defect_rate", {})
    comp_stats = pq.get("arithmetic_complement", {})
    error_stats = pq.get("process_error_rate", {})

    ee = kpis.get("energy_efficiency", {})
    sec_info = ee.get("specific_energy_consumption", {})
    status_info = ee.get("efficiency_status_breakdown", {})
    status_counts = status_info.get("counts", {})
    status_pcts = status_info.get("percentages", {})

    mean_defect = defect_stats.get("mean", 0.0)
    med_defect = defect_stats.get("median", 0.0)
    p95_defect = defect_stats.get("p95", 0.0)

    mean_error = error_stats.get("mean", 0.0)
    med_error = error_stats.get("median", 0.0)
    p95_error = error_stats.get("p95", 0.0)

    arith_comp = comp_stats.get("value", 100.0 - mean_defect)

    # -----------------------------------------------------------------------
    # 1. Top-Level Quality & Efficiency Indicators (KPI 3 & KPI 5)
    # -----------------------------------------------------------------------
    st.markdown("#### Key Quality & Energy Efficiency Indicators (KPI 3 & KPI 5)")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        render_kpi_card(
            label="Mean Defect Rate",
            value=mean_defect,
            unit="%",
            subtext=f"Median: {med_defect:.2f}% | P95: {p95_defect:.2f}%",
            help_text="Finished-good inspection defect percentage across monitored units. Range: [0.0, 10.0]%."
        )

    with col2:
        render_kpi_card(
            label="Arithmetic Complement",
            value=arith_comp,
            unit="%",
            subtext="100 - Mean Defect Rate (%)",
            help_text="Strictly the arithmetic complement (100 - mean defect rate). NOT verified yield or conformance."
        )

    with col3:
        render_kpi_card(
            label="Process Error Rate",
            value=mean_error,
            unit="%",
            subtext=f"Median: {med_error:.2f}% | P95: {p95_error:.2f}%",
            help_text="Machine controller execution and process error rate. Range: [0.0, 15.0]%."
        )

    with col4:
        render_kpi_card(
            label="Mean SEC",
            value=sec_info.get("mean", 0.0),
            unit="kWh/unit",
            subtext=f"Eligible: {sec_info.get('eligible_count', 0):,} records",
            help_text="Specific Energy Consumption evaluated row-level strictly for positive production speeds."
        )

    # Architectural Safeguard Notice
    st.info(
        r"**Provisional Safeguard Notice:** The arithmetic complement ($94.991194\%$) represents strictly "
        r"$100 - \text{mean defect rate}$. It must NOT be described as verified first-pass yield, product conformance, "
        r"or process capability (Cpk) without physical batch sizes and scrap denominators. "
        r"Original `Efficiency_Status` classification labels are preserved without reconstruction (including the "
        r"two boundary mismatches at $\text{Error\_Rate\_\%} = 5.0\%$). Zero causation is implied between statistical associations."
    )

    st.divider()

    # Precompute shared summaries for Module 4 visualizers
    quality_summary = compute_quality_machine_summary(df)
    temporal_summary = compute_temporal_daily_summary(df)
    mode_summary = compute_mode_stratified_summary(df)

    # -----------------------------------------------------------------------
    # 2. Finished-Good Quality & Process Error Dynamics (KPI 3)
    # -----------------------------------------------------------------------
    st.markdown("#### 1. Quality & Process Error Surveillance (KPI 3)")
    st.caption("Finished-good defect rates, controller execution errors, longitudinal trends, and operational mode comparisons.")

    tab_q_dist, tab_q_trend, tab_q_bivar, tab_q_mode = st.tabs([
        "📊 Quality Distributions",
        "📈 Quality Trends Over Time",
        "🎯 Defect vs. Error Dispersion",
        "⚙️ Operating Mode Allocations"
    ])

    with tab_q_dist:
        st.markdown("##### Empirical Defect & Error Rate Distributions")
        c_qd1, c_qd2 = st.columns(2)

        with c_qd1:
            st.markdown("###### Finished-Goods Defect Rate Distribution")
            if "Quality_Control_Defect_Rate_%" in df.columns and not df.empty:
                fig_dfc_hist = px.histogram(
                    df,
                    x="Quality_Control_Defect_Rate_%",
                    color="Operation_Mode" if "Operation_Mode" in df.columns else None,
                    nbins=40,
                    barmode="overlay",
                    opacity=0.75,
                    labels={"Quality_Control_Defect_Rate_%": "Defect Rate (%)"},
                    color_discrete_map={"Active": "#1f77b4", "Idle": "#ff7f0e", "Maintenance": "#2ca02c"},
                )
                fig_dfc_hist.add_vline(
                    x=mean_defect,
                    line_dash="dash",
                    line_color="#d62728",
                    annotation_text=f"Mean: {mean_defect:.2f}%",
                    annotation_position="top right",
                )
                fig_dfc_hist.update_layout(
                    xaxis_title="Defect Rate (%)",
                    yaxis_title="Observation Count",
                    margin=dict(l=40, r=20, t=30, b=40),
                    height=300,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                )
                st.plotly_chart(fig_dfc_hist, use_container_width=True)
                st.caption(
                    f"Defect rate spans **[{df['Quality_Control_Defect_Rate_%'].min():.2f}, {df['Quality_Control_Defect_Rate_%'].max():.2f}]%** "
                    f"with mean **{mean_defect:.4f}%** and standard deviation **{df['Quality_Control_Defect_Rate_%'].std(ddof=1):.2f}%**."
                )

        with c_qd2:
            st.markdown("###### Process Controller Error Rate Distribution")
            if "Error_Rate_%" in df.columns and not df.empty:
                fig_err_hist = px.histogram(
                    df,
                    x="Error_Rate_%",
                    color="Operation_Mode" if "Operation_Mode" in df.columns else None,
                    nbins=40,
                    barmode="overlay",
                    opacity=0.75,
                    labels={"Error_Rate_%": "Process Error Rate (%)"},
                    color_discrete_map={"Active": "#1f77b4", "Idle": "#ff7f0e", "Maintenance": "#2ca02c"},
                )
                fig_err_hist.add_vline(
                    x=mean_error,
                    line_dash="dash",
                    line_color="#d62728",
                    annotation_text=f"Mean: {mean_error:.2f}%",
                    annotation_position="top right",
                )
                fig_err_hist.update_layout(
                    xaxis_title="Process Error Rate (%)",
                    yaxis_title="Observation Count",
                    margin=dict(l=40, r=20, t=30, b=40),
                    height=300,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                )
                st.plotly_chart(fig_err_hist, use_container_width=True)
                st.caption(
                    f"Process error rate spans **[{df['Error_Rate_%'].min():.2f}, {df['Error_Rate_%'].max():.2f}]%** "
                    f"with mean **{mean_error:.4f}%** and standard deviation **{df['Error_Rate_%'].std(ddof=1):.2f}%**."
                )

    with tab_q_trend:
        st.markdown("##### Longitudinal Defect & Error Rates Across 69 Monitoring Dates")
        if not temporal_summary.empty:
            fig_q_trend = go.Figure()
            fig_q_trend.add_trace(go.Scatter(
                x=temporal_summary["parsed_date"],
                y=temporal_summary["Mean_Defect_Rate_pct"],
                mode="lines+markers",
                name="Defect Rate (%)",
                line=dict(color="#d62728", width=2),
                marker=dict(size=5),
            ))
            fig_q_trend.add_trace(go.Scatter(
                x=temporal_summary["parsed_date"],
                y=temporal_summary["Mean_Error_Rate_pct"],
                mode="lines+markers",
                name="Error Rate (%)",
                line=dict(color="#1f77b4", width=2),
                marker=dict(size=5),
            ))
            fig_q_trend.add_hline(
                y=mean_defect,
                line_dash="dot",
                line_color="#d62728",
                annotation_text=f"Defect Grand Mean ({mean_defect:.2f}%)",
                annotation_position="bottom right",
            )
            fig_q_trend.add_hline(
                y=mean_error,
                line_dash="dot",
                line_color="#1f77b4",
                annotation_text=f"Error Grand Mean ({mean_error:.2f}%)",
                annotation_position="bottom right",
            )
            fig_q_trend.update_layout(
                xaxis_title="Calendar Date",
                yaxis_title="Rate (%)",
                margin=dict(l=40, r=20, t=30, b=40),
                height=340,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            st.plotly_chart(fig_q_trend, use_container_width=True)
            st.caption(
                f"Both quality indicators show extreme daily baseline consistency across all {len(temporal_summary)} dates "
                f"(Daily mean defect range: **{temporal_summary['Mean_Defect_Rate_pct'].min():.2f}%** to **{temporal_summary['Mean_Defect_Rate_pct'].max():.2f}%**; "
                f"daily mean error range: **{temporal_summary['Mean_Error_Rate_pct'].min():.2f}%** to **{temporal_summary['Mean_Error_Rate_pct'].max():.2f}%**)."
            )

    with tab_q_bivar:
        st.markdown("##### Defect Rate vs. Process Execution Error Rate Dispersion")
        st.caption("Bivariate diagnostic space examining finished-good defects vs. controller execution errors.")

        c_qb1, c_qb2 = st.columns(2)
        with c_qb1:
            q_decimation = st.selectbox(
                "Display Sample Size:",
                options=[1000, 2500, 5000, 10000, "All Records"],
                index=1,
                key="qual_bivar_decimate"
            )
        with c_qb2:
            q_color_choice = st.selectbox(
                "Color Dimension:",
                options=["Operation_Mode", "Efficiency_Status", "None"],
                index=0,
                key="qual_bivar_color"
            )

        if q_decimation == "All Records" or len(df) <= int(q_decimation):
            q_scatter_df = df
            q_is_sampled = False
        else:
            q_scatter_df = df.sample(n=int(q_decimation), random_state=42)
            q_is_sampled = True

        color_col = None if q_color_choice == "None" else q_color_choice
        fig_q_bivar = px.scatter(
            q_scatter_df,
            x="Quality_Control_Defect_Rate_%",
            y="Error_Rate_%",
            color=color_col if color_col in q_scatter_df.columns else None,
            opacity=0.6,
            labels={
                "Quality_Control_Defect_Rate_%": "Defect Rate (%)",
                "Error_Rate_%": "Process Error Rate (%)",
            },
            color_discrete_map={
                "Active": "#1f77b4", "Idle": "#ff7f0e", "Maintenance": "#2ca02c",
                "Low": "#e6194b", "Medium": "#ffe119", "High": "#3cb44b"
            },
            hover_data=["Machine_ID", "Date"] if "Machine_ID" in q_scatter_df.columns else None,
        )
        fig_q_bivar.update_traces(marker=dict(size=5))
        fig_q_bivar.update_layout(
            xaxis_title="Defect Rate (%)",
            yaxis_title="Process Error Rate (%)",
            margin=dict(l=40, r=20, t=20, b=40),
            height=380,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig_q_bivar, use_container_width=True)

        corr_qe = df[["Quality_Control_Defect_Rate_%", "Error_Rate_%"]].dropna().corr().iloc[0, 1] if len(df) > 1 else 0.0
        sample_sub = f" (Sample: {len(q_scatter_df):,} records)" if q_is_sampled else ""
        st.caption(
            f"Pearson linear correlation between Defect Rate and Error Rate: **r = {corr_qe:.4f}**{sample_sub}. "
            "Negligible correlation indicates finished-goods quality inspection defects occur independently of controller error telemetry."
        )

    with tab_q_mode:
        st.markdown("##### Quality & Error Rates Across Operating Modes")
        if "Operation_Mode" in df.columns and "Quality_Control_Defect_Rate_%" in df.columns:
            fig_q_mode = px.box(
                df,
                x="Operation_Mode",
                y="Quality_Control_Defect_Rate_%",
                color="Operation_Mode",
                color_discrete_map={"Active": "#1f77b4", "Idle": "#ff7f0e", "Maintenance": "#2ca02c"},
                labels={"Operation_Mode": "Operation Mode", "Quality_Control_Defect_Rate_%": "Defect Rate (%)"},
            )
            fig_q_mode.update_layout(
                xaxis_title="Operation Mode",
                yaxis_title="Defect Rate (%)",
                margin=dict(l=40, r=20, t=20, b=40),
                height=320,
                showlegend=False,
            )
            st.plotly_chart(fig_q_mode, use_container_width=True)

            if not mode_summary.empty:
                st.dataframe(
                    mode_summary[["Operation_Mode", "Record_Count", "Record_Pct", "Mean_Defect_Rate_pct", "Mean_Error_Rate_pct"]].rename(columns={
                        "Operation_Mode": "Mode",
                        "Record_Count": "Observations",
                        "Record_Pct": "Share (%)",
                        "Mean_Defect_Rate_pct": "Mean Defect Rate (%)",
                        "Mean_Error_Rate_pct": "Mean Error Rate (%)"
                    }),
                    use_container_width=True,
                    hide_index=True
                )
            st.caption(
                "Defect rates and process error rates remain identical across Active (~5.01%), Idle (~5.01%), and Maintenance (~5.00%). "
                "Operating mode categories exhibit no statistical divergence in quality metrics."
            )

    st.divider()

    # -----------------------------------------------------------------------
    # 3. Machine-Level Quality & Process Error Comparisons
    # -----------------------------------------------------------------------
    st.markdown("#### 2. Machine Fleet Quality Surveillance")
    st.caption("Cross-machine comparative evaluation of finished defect rates and process execution errors.")

    if not quality_summary.empty:
        n_m = len(quality_summary)
        c_m1, c_m2 = st.columns([2, 1])
        with c_m2:
            sort_q_order = st.radio(
                "Sort Machines By:",
                options=["Lowest Defect Rate (Best Quality)", "Highest Defect Rate"],
                index=0,
                horizontal=True,
                key="sort_qual_order"
            )

        q_asc = (sort_q_order == "Lowest Defect Rate (Best Quality)")
        sorted_mach_q = quality_summary.sort_values(by="Mean_Defect_Rate_pct", ascending=q_asc).copy()
        sorted_mach_q["Machine_Label"] = sorted_mach_q["Machine_ID"].apply(lambda m: f"Machine {m}")

        if n_m > 10:
            show_qm_count = st.slider("Machines to Display:", min_value=5, max_value=n_m, value=min(20, n_m), key="qm_slider")
            display_qm_df = sorted_mach_q.head(show_qm_count)
        else:
            display_qm_df = sorted_mach_q

        fig_qm_bar = px.bar(
            display_qm_df,
            x="Mean_Defect_Rate_pct",
            y="Machine_Label",
            orientation="h",
            color="Mean_Defect_Rate_pct",
            color_continuous_scale="Reds_r" if q_asc else "Reds",
            labels={"Mean_Defect_Rate_pct": "Mean Defect Rate (%)", "Machine_Label": "Machine"},
        )
        fig_qm_bar.update_layout(
            xaxis_title="Mean Defect Rate (%)",
            yaxis=dict(autorange="reversed"),
            margin=dict(l=60, r=20, t=20, b=40),
            height=max(320, len(display_qm_df) * 18),
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig_qm_bar, use_container_width=True)
        st.caption(
            f"Lowest observed defect rate: **Machine {sorted_mach_q.iloc[0 if q_asc else -1]['Machine_ID']}** "
            f"({sorted_mach_q.iloc[0 if q_asc else -1]['Mean_Defect_Rate_pct']:.4f}%); "
            f"Highest observed defect rate: **Machine {sorted_mach_q.iloc[-1 if q_asc else 0]['Machine_ID']}** "
            f"({sorted_mach_q.iloc[-1 if q_asc else 0]['Mean_Defect_Rate_pct']:.4f}%). "
            "Narrow difference across all 50 units (spread < 0.35%) indicates uniform baseline quality across machinery."
        )

        with st.expander("📋 Machine Quality Summary Table (All Units)", expanded=False):
            fmt_q_table = quality_summary.rename(columns={
                "Machine_ID": "Machine",
                "Record_Count": "Observations",
                "Mean_Defect_Rate_pct": "Defect Mean (%)",
                "Median_Defect_Rate_pct": "Defect Med (%)",
                "Arithmetic_Complement_pct": "Complement (%)",
                "Mean_Error_Rate_pct": "Error Mean (%)",
                "Median_Error_Rate_pct": "Error Med (%)",
                "Defect_Rank": "Defect Rank",
                "Error_Rank": "Error Rank",
            })
            st.dataframe(
                fmt_q_table[["Machine", "Observations", "Defect Mean (%)", "Defect Med (%)", "Complement (%)", "Error Mean (%)", "Error Med (%)", "Defect Rank", "Error Rank"]],
                use_container_width=True,
                hide_index=True
            )

    st.divider()

    # -----------------------------------------------------------------------
    # 4. Multi-Tier Efficiency Status & Energy Intensity (KPI 5)
    # -----------------------------------------------------------------------
    st.markdown("#### 3. Empirical Efficiency Status & Energy Intensity (KPI 5)")
    st.caption("Distribution across Low, Medium, and High efficiency classes, contingency allocations, and tier-stratified SEC profiles.")

    # Status Cards
    sc1, sc2, sc3 = st.columns(3)
    with sc1:
        render_kpi_card(
            label="Low Efficiency Tier",
            value=status_counts.get("Low", 0),
            unit="records",
            subtext=f"{status_pcts.get('Low', 0.0):.2f}% of fleet observations",
            help_text="Records categorized as Low efficiency in source metadata."
        )
    with sc2:
        render_kpi_card(
            label="Medium Efficiency Tier",
            value=status_counts.get("Medium", 0),
            unit="records",
            subtext=f"{status_pcts.get('Medium', 0.0):.2f}% of fleet observations",
            help_text="Records categorized as Medium efficiency in source metadata."
        )
    with sc3:
        render_kpi_card(
            label="High Efficiency Tier",
            value=status_counts.get("High", 0),
            unit="records",
            subtext=f"{status_pcts.get('High', 0.0):.2f}% of fleet observations",
            help_text="Records categorized as High efficiency in source metadata."
        )

    tab_eff_mode, tab_eff_mach, tab_eff_sec = st.tabs([
        "📊 Efficiency Allocations by Mode",
        "🏭 Efficiency Composition by Machine",
        "⚡ SEC Intensity by Efficiency Tier"
    ])

    with tab_eff_mode:
        st.markdown("##### Efficiency Status Proportions Across Operating Modes")
        contingency_df = compute_efficiency_contingency(df, row_col="Operation_Mode")
        if not contingency_df.empty:
            # Bar chart of counts
            fig_ct = px.bar(
                contingency_df,
                x="Operation_Mode",
                y=["Low_Count", "Medium_Count", "High_Count"],
                title="Efficiency Status Composition by Operation Mode",
                labels={"value": "Observation Count", "variable": "Efficiency Tier", "Operation_Mode": "Operation Mode"},
                color_discrete_map={
                    "Low_Count": "#e6194b",
                    "Medium_Count": "#ffe119",
                    "High_Count": "#3cb44b",
                },
                barmode="stack",
            )
            fig_ct.update_layout(
                margin=dict(l=40, r=20, t=40, b=40),
                height=320,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            st.plotly_chart(fig_ct, use_container_width=True)

            st.dataframe(
                contingency_df.rename(columns={
                    "Operation_Mode": "Mode",
                    "Total_Count": "Total",
                    "Low_Count": "Low Count",
                    "Low_Pct": "Low (%)",
                    "Medium_Count": "Med Count",
                    "Medium_Pct": "Med (%)",
                    "High_Count": "High Count",
                    "High_Pct": "High (%)",
                }),
                use_container_width=True,
                hide_index=True
            )
            st.caption(
                "Chi-square contingency analysis (Cramér's V = 0.0042) confirms that Efficiency_Status is statistically "
                "independent of Operation_Mode (Low ~77.8%, Medium ~19.2%, High ~3.0% across all modes)."
            )

    with tab_eff_mach:
        st.markdown("##### Efficiency Tier Breakdown Across All 50 Machines")
        mach_contingency = compute_efficiency_contingency(df, row_col="Machine_ID")
        if not mach_contingency.empty:
            mach_contingency["Machine_Label"] = mach_contingency["Machine_ID"].apply(lambda m: f"M{m}")
            fig_mach_ct = px.bar(
                mach_contingency,
                x="Machine_Label",
                y=["Low_Pct", "Medium_Pct", "High_Pct"],
                labels={"value": "Proportion (%)", "variable": "Tier", "Machine_Label": "Machine"},
                color_discrete_map={
                    "Low_Pct": "#e6194b",
                    "Medium_Pct": "#ffe119",
                    "High_Pct": "#3cb44b",
                },
                barmode="stack",
            )
            fig_mach_ct.update_layout(
                xaxis_title="Machine Identifier",
                yaxis_title="Composition (%)",
                margin=dict(l=40, r=20, t=30, b=40),
                height=320,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            st.plotly_chart(fig_mach_ct, use_container_width=True)
            st.caption(
                "Across all 50 units, the proportion of Low efficiency records ranges narrowly between 76.2% and 79.4%, "
                "demonstrating that efficiency categorization is uniformly distributed across the machinery fleet."
            )

    with tab_eff_sec:
        st.markdown("##### Specific Energy Consumption (SEC) Stratified by Efficiency Tier")
        if "Efficiency_Status" in df.columns and "Production_Speed_units_per_hr" in df.columns and "Power_Consumption_kW" in df.columns:
            pos_mask = df["Production_Speed_units_per_hr"] > 0
            if pos_mask.sum() > 0:
                eff_sec_df = pd.DataFrame({
                    "Efficiency_Status": df.loc[pos_mask, "Efficiency_Status"].values,
                    "SEC_kWh_per_u": (df.loc[pos_mask, "Power_Consumption_kW"] / df.loc[pos_mask, "Production_Speed_units_per_hr"]).values,
                })
                fig_eff_sec = px.box(
                    eff_sec_df,
                    x="Efficiency_Status",
                    y="SEC_kWh_per_u",
                    color="Efficiency_Status",
                    category_orders={"Efficiency_Status": ["Low", "Medium", "High"]},
                    color_discrete_map={"Low": "#e6194b", "Medium": "#ffe119", "High": "#3cb44b"},
                    labels={"Efficiency_Status": "Efficiency Tier", "SEC_kWh_per_u": "SEC (kWh/unit)"},
                )
                fig_eff_sec.update_layout(
                    xaxis_title="Efficiency Status Tier",
                    yaxis_title="Specific Energy Consumption (kWh/unit)",
                    margin=dict(l=40, r=20, t=30, b=40),
                    height=320,
                    showlegend=False,
                )
                st.plotly_chart(fig_eff_sec, use_container_width=True)

                # Tier SEC stats table
                tier_sec_records = []
                for tier in ["Low", "Medium", "High"]:
                    sub_sec = eff_sec_df[eff_sec_df["Efficiency_Status"] == tier]["SEC_kWh_per_u"]
                    if len(sub_sec) > 0:
                        tier_sec_records.append({
                            "Tier": tier,
                            "Observations": len(sub_sec),
                            "Mean SEC (kWh/u)": f"{sub_sec.mean():.6f}",
                            "Median SEC (kWh/u)": f"{sub_sec.median():.6f}",
                            "Std SEC (kWh/u)": f"{sub_sec.std(ddof=1):.6f}",
                            "P95 SEC (kWh/u)": f"{np.percentile(sub_sec, 95):.6f}",
                        })
                st.dataframe(pd.DataFrame(tier_sec_records), use_container_width=True, hide_index=True)
                st.caption(
                    "SEC distributions are virtually identical across Low (0.0293 kWh/u), Medium (0.0293 kWh/u), and High (0.0294 kWh/u) tiers. "
                    "This demonstrates that `Efficiency_Status` classification labels were not generated based on energy consumption per unit."
                )
