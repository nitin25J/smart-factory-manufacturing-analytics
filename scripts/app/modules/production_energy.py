"""
Module 3: Production Throughput & Energy Performance.
Manufacturing Diagnostic Intelligence System — Phase 2.5.

Target Diagnostic Pillars:
- Production Performance & Fleet Throughput (KPI 2).
- Operational Mode Allocations & Electrical Power Demand Baselines.
- Energy-Adjusted Efficiency: Specific Energy Consumption (SEC) (KPI 5).

Responsibilities:
- Surfaces fleet-wide throughput across all three operation modes (Active, Idle, Maintenance).
- Analyzes empirical production speed distributions, machine rankings, and temporal dynamics.
- Evaluates machine electrical power demand profiles, trends, and mode allocations.
- Computes and visualizes row-level Specific Energy Consumption (SEC) in kWh/unit for positive speeds.
- Strictly enforces capacity utilization and energy savings safeguards.
"""

from __future__ import annotations

from typing import Any, Dict

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from scripts.app.analytics import (
    compute_mode_stratified_summary,
    compute_production_energy_summary,
    compute_temporal_daily_summary,
)
from scripts.app.components import render_empty_state, render_kpi_card, render_section_header


def render_production_energy(df: pd.DataFrame, kpis: Dict[str, Any]) -> None:
    """
    Render Module 3: Production Throughput & Energy Performance analytical interface.

    Parameters:
        df: Filtered or full DataFrame slice for throughput and energy monitoring.
        kpis: Pre-calculated KPI dictionary from kpi_engine.
    """
    render_section_header(
        title="Module 3: Production Throughput & Energy Performance",
        description="Fleet throughput rates, operational mode allocations, power demand, and specific energy consumption (SEC) baselines.",
    )

    if df.empty:
        render_empty_state(
            title="No Production Data Found",
            message="No records match your active filter selection.",
            suggestion="Adjust your sidebar filters to include more machines or operation modes."
        )
        return

    n_total = len(df)
    n_machines = df["Machine_ID"].nunique() if "Machine_ID" in df.columns else 0

    otr = kpis.get("operational_throughput", {})
    fleet_speed = otr.get("fleet_throughput", {})
    modes_speed = otr.get("mode_stratified_throughput", {})

    ee = kpis.get("energy_efficiency", {})
    sec_info = ee.get("specific_energy_consumption", {})

    power_series = df["Power_Consumption_kW"].dropna() if "Power_Consumption_kW" in df.columns else pd.Series(dtype=float)
    power_mean = float(power_series.mean()) if len(power_series) > 0 else 0.0
    power_median = float(power_series.median()) if len(power_series) > 0 else 0.0
    power_p95 = float(np.percentile(power_series, 95)) if len(power_series) >= 20 else (float(power_series.max()) if len(power_series) > 0 else 0.0)

    # -----------------------------------------------------------------------
    # 1. Top-Level Production & Energy Indicators (KPI 2 & KPI 5)
    # -----------------------------------------------------------------------
    st.markdown("#### Key Production & Energy Demand Indicators (KPI 2 & KPI 5)")
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
            label="Fleet Mean Speed",
            value=fleet_speed.get("mean", 0.0),
            unit="units/hr",
            subtext=f"Median: {fleet_speed.get('median', 0.0):.1f} u/hr | P95: {fleet_speed.get('p95', 0.0):.1f} u/hr",
            help_text="Fleet-wide empirical manufacturing throughput rate across all operation modes."
        )

    with col3:
        render_kpi_card(
            label="Mean Power Demand",
            value=power_mean,
            unit="kW",
            subtext=f"Median: {power_median:.2f} kW | P95: {power_p95:.2f} kW",
            help_text="Observed machine-level electrical power demand telemetry. Range: [1.5, 10.0] kW."
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
        "**Provisional Safeguard Notice:** Throughput is reported strictly as empirical production speed in units/hr. "
        "The observed sample maximum (~500 units/hr) is NOT treated as verified rated machine capacity. Capacity utilization "
        "percentages and production quotas remain uncalculated pending manufacturer nameplate specifications. "
        "Machine power draw (kW) must NOT be represented as facility-wide total energy consumption, and energy savings "
        "claims are invalid without baseline specifications."
    )

    st.divider()

    # Precompute shared summaries for Module 3 visualizers
    prod_energy_summary = compute_production_energy_summary(df)
    temporal_summary = compute_temporal_daily_summary(df)
    mode_summary = compute_mode_stratified_summary(df)

    # -----------------------------------------------------------------------
    # 2. Production Speed & Throughput Dynamics (KPI 2)
    # -----------------------------------------------------------------------
    st.markdown("#### 1. Production Throughput Surveillance (KPI 2)")
    st.caption("Distribution, longitudinal trends, machine comparative rankings, and mode-stratified throughput rates.")

    tab_sp_dist, tab_sp_trend, tab_sp_mach, tab_sp_mode = st.tabs([
        "📊 Speed Distribution",
        "📈 Speed Trends Over Time",
        "🏭 Machine Speed Rankings",
        "⚙️ Operating Mode Allocations"
    ])

    with tab_sp_dist:
        st.markdown("##### Empirical Production Speed Distribution")
        if "Production_Speed_units_per_hr" in df.columns and not df.empty:
            color_dim = "Operation_Mode" if "Operation_Mode" in df.columns else None
            fig_sp_hist = px.histogram(
                df,
                x="Production_Speed_units_per_hr",
                color=color_dim,
                nbins=40,
                barmode="overlay",
                opacity=0.75,
                labels={"Production_Speed_units_per_hr": "Production Speed (units/hr)"},
                color_discrete_map={"Active": "#1f77b4", "Idle": "#ff7f0e", "Maintenance": "#2ca02c"},
            )
            mean_speed_val = fleet_speed.get("mean", float(df["Production_Speed_units_per_hr"].mean()))
            fig_sp_hist.add_vline(
                x=mean_speed_val,
                line_dash="dash",
                line_color="#d62728",
                annotation_text=f"Mean: {mean_speed_val:.1f} u/hr",
                annotation_position="top right",
            )
            fig_sp_hist.update_layout(
                xaxis_title="Production Speed (units/hr)",
                yaxis_title="Observation Count",
                margin=dict(l=40, r=20, t=30, b=40),
                height=340,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            st.plotly_chart(fig_sp_hist, use_container_width=True)
            st.caption(
                f"Fleet speed spans **[{df['Production_Speed_units_per_hr'].min():.1f}, {df['Production_Speed_units_per_hr'].max():.1f}] units/hr** "
                f"with empirical mean **{mean_speed_val:.2f} units/hr** and standard deviation **{df['Production_Speed_units_per_hr'].std(ddof=1):.2f} units/hr**. "
                "The distribution is continuous and uniform across the observed operational range."
            )

    with tab_sp_trend:
        st.markdown("##### Longitudinal Production Speed Trends Across Calendar Dates")
        if not temporal_summary.empty:
            fig_sp_trend = px.line(
                temporal_summary,
                x="parsed_date",
                y="Mean_Speed_u_per_hr",
                markers=True,
                labels={"parsed_date": "Calendar Date", "Mean_Speed_u_per_hr": "Daily Mean Speed (units/hr)"},
                title="Daily Mean Throughput (units/hr)",
            )
            fig_sp_trend.add_hline(
                y=fleet_speed.get("mean", 275.92),
                line_dash="dot",
                line_color="#7f7f7f",
                annotation_text="Fleet Grand Mean",
                annotation_position="bottom right",
            )
            fig_sp_trend.update_layout(
                xaxis_title="Calendar Date",
                yaxis_title="Mean Production Speed (units/hr)",
                margin=dict(l=40, r=20, t=40, b=40),
                height=340,
            )
            st.plotly_chart(fig_sp_trend, use_container_width=True)
            st.caption(
                f"Evaluated across **{len(temporal_summary)} calendar dates**. Daily mean speed exhibits tight stability "
                f"around the fleet baseline (daily range: **{temporal_summary['Mean_Speed_u_per_hr'].min():.1f}** to "
                f"**{temporal_summary['Mean_Speed_u_per_hr'].max():.1f} units/hr**)."
            )

    with tab_sp_mach:
        st.markdown("##### Machine-Level Production Speed Comparisons")
        if not prod_energy_summary.empty:
            n_m = len(prod_energy_summary)
            c_rank1, c_rank2 = st.columns([2, 1])
            with c_rank2:
                sort_order = st.radio(
                    "Sort By Speed:",
                    options=["Highest to Lowest", "Lowest to Highest"],
                    index=0,
                    horizontal=True,
                    key="sort_speed_order"
                )
            
            ascending = (sort_order == "Lowest to Highest")
            sorted_mach_speed = prod_energy_summary.sort_values(by="Mean_Speed_u_per_hr", ascending=ascending).copy()
            sorted_mach_speed["Machine_Label"] = sorted_mach_speed["Machine_ID"].apply(lambda m: f"Machine {m}")

            # Control display slice
            if n_m > 10:
                show_count = st.slider("Machines to Display:", min_value=5, max_value=n_m, value=min(20, n_m), key="speed_mach_slider")
                display_df = sorted_mach_speed.head(show_count)
            else:
                display_df = sorted_mach_speed

            fig_sp_mach = px.bar(
                display_df,
                x="Mean_Speed_u_per_hr",
                y="Machine_Label",
                orientation="h",
                color="Mean_Speed_u_per_hr",
                color_continuous_scale="Viridis",
                labels={"Mean_Speed_u_per_hr": "Mean Speed (units/hr)", "Machine_Label": "Machine"},
            )
            fig_sp_mach.update_layout(
                xaxis_title="Mean Production Speed (units/hr)",
                yaxis=dict(autorange="reversed"),
                margin=dict(l=60, r=20, t=20, b=40),
                height=max(320, len(display_df) * 18),
                coloraxis_showscale=False,
            )
            st.plotly_chart(fig_sp_mach, use_container_width=True)
            st.caption(
                f"Top-performing unit: **Machine {sorted_mach_speed.iloc[-1 if ascending else 0]['Machine_ID']}** "
                f"({sorted_mach_speed.iloc[-1 if ascending else 0]['Mean_Speed_u_per_hr']:.2f} u/hr); "
                f"Lowest unit: **Machine {sorted_mach_speed.iloc[0 if ascending else -1]['Machine_ID']}** "
                f"({sorted_mach_speed.iloc[0 if ascending else -1]['Mean_Speed_u_per_hr']:.2f} u/hr). "
                "Narrow spread demonstrates homogeneous production scheduling across equipment."
            )

    with tab_sp_mode:
        st.markdown("##### Production Speed Across Operating Modes")
        if "Operation_Mode" in df.columns and "Production_Speed_units_per_hr" in df.columns:
            fig_sp_mode = px.box(
                df,
                x="Operation_Mode",
                y="Production_Speed_units_per_hr",
                color="Operation_Mode",
                color_discrete_map={"Active": "#1f77b4", "Idle": "#ff7f0e", "Maintenance": "#2ca02c"},
                labels={"Operation_Mode": "Operation Mode", "Production_Speed_units_per_hr": "Production Speed (units/hr)"},
            )
            fig_sp_mode.update_layout(
                xaxis_title="Operation Mode",
                yaxis_title="Production Speed (units/hr)",
                margin=dict(l=40, r=20, t=20, b=40),
                height=320,
                showlegend=False,
            )
            st.plotly_chart(fig_sp_mode, use_container_width=True)

            if not mode_summary.empty:
                st.dataframe(
                    mode_summary[["Operation_Mode", "Record_Count", "Record_Pct", "Mean_Speed_u_per_hr", "Std_Speed_u_per_hr"]].rename(columns={
                        "Operation_Mode": "Mode",
                        "Record_Count": "Observations",
                        "Record_Pct": "Share (%)",
                        "Mean_Speed_u_per_hr": "Mean Speed (u/hr)",
                        "Std_Speed_u_per_hr": "Speed Std (u/hr)"
                    }),
                    use_container_width=True,
                    hide_index=True
                )
            st.caption(
                "Note: Speed is recorded across all three modes (Active, Idle, Maintenance) with virtually identical "
                "descriptive means (~274 to ~278 units/hr). This confirms that operation mode tags do not gate physical "
                "spindle rotation telemetry in this dataset."
            )

    st.divider()

    # -----------------------------------------------------------------------
    # 3. Electrical Power Demand Baselines
    # -----------------------------------------------------------------------
    st.markdown("#### 2. Electrical Power Consumption Analysis")
    st.caption("Empirical power demand baselines, diurnal and longitudinal timelines, and mode-stratified power draw.")

    tab_pw_dist, tab_pw_trend, tab_pw_mach, tab_pw_mode = st.tabs([
        "📊 Power Distribution",
        "📈 Power Demand Over Time",
        "🏭 Machine Power Comparisons",
        "⚙️ Operating Mode Allocations"
    ])

    with tab_pw_dist:
        st.markdown("##### Empirical Power Consumption Distribution")
        if "Power_Consumption_kW" in df.columns and not df.empty:
            color_dim = "Operation_Mode" if "Operation_Mode" in df.columns else None
            fig_pw_hist = px.histogram(
                df,
                x="Power_Consumption_kW",
                color=color_dim,
                nbins=40,
                barmode="overlay",
                opacity=0.75,
                labels={"Power_Consumption_kW": "Power Consumption (kW)"},
                color_discrete_map={"Active": "#1f77b4", "Idle": "#ff7f0e", "Maintenance": "#2ca02c"},
            )
            fig_pw_hist.add_vline(
                x=power_mean,
                line_dash="dash",
                line_color="#d62728",
                annotation_text=f"Mean: {power_mean:.2f} kW",
                annotation_position="top right",
            )
            fig_pw_hist.update_layout(
                xaxis_title="Power Consumption (kW)",
                yaxis_title="Observation Count",
                margin=dict(l=40, r=20, t=30, b=40),
                height=340,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            st.plotly_chart(fig_pw_hist, use_container_width=True)
            st.caption(
                f"Fleet power consumption spans **[{df['Power_Consumption_kW'].min():.2f}, {df['Power_Consumption_kW'].max():.2f}] kW** "
                f"with mean **{power_mean:.2f} kW** (std: **{power_series.std(ddof=1):.2f} kW**). "
                "Power demand is continuous and bounded across the 1.5–10.0 kW operating envelope."
            )

    with tab_pw_trend:
        st.markdown("##### Daily Electrical Power Demand Trends")
        if not temporal_summary.empty:
            fig_pw_trend = px.line(
                temporal_summary,
                x="parsed_date",
                y="Mean_Power_kW",
                markers=True,
                labels={"parsed_date": "Calendar Date", "Mean_Power_kW": "Daily Mean Power (kW)"},
                title="Daily Mean Electrical Power Demand (kW)",
                color_discrete_sequence=["#ff7f0e"],
            )
            fig_pw_trend.add_hline(
                y=power_mean,
                line_dash="dot",
                line_color="#7f7f7f",
                annotation_text="Fleet Mean Power",
                annotation_position="bottom right",
            )
            fig_pw_trend.update_layout(
                xaxis_title="Calendar Date",
                yaxis_title="Mean Power Demand (kW)",
                margin=dict(l=40, r=20, t=40, b=40),
                height=340,
            )
            st.plotly_chart(fig_pw_trend, use_container_width=True)
            st.caption(
                f"Longitudinal daily power draw remains tightly clustered between **{temporal_summary['Mean_Power_kW'].min():.2f} kW** "
                f"and **{temporal_summary['Mean_Power_kW'].max():.2f} kW** across all 69 monitoring dates."
            )

    with tab_pw_mach:
        st.markdown("##### Machine-Level Electrical Power Demand Comparisons")
        if not prod_energy_summary.empty:
            n_m = len(prod_energy_summary)
            c_p1, c_p2 = st.columns([2, 1])
            with c_p2:
                sort_p_order = st.radio(
                    "Sort By Power:",
                    options=["Lowest to Highest (Efficient)", "Highest to Lowest"],
                    index=0,
                    horizontal=True,
                    key="sort_power_order"
                )
            
            p_ascending = (sort_p_order == "Lowest to Highest (Efficient)")
            sorted_mach_power = prod_energy_summary.sort_values(by="Mean_Power_kW", ascending=p_ascending).copy()
            sorted_mach_power["Machine_Label"] = sorted_mach_power["Machine_ID"].apply(lambda m: f"Machine {m}")

            if n_m > 10:
                show_p_count = st.slider("Machines to Display:", min_value=5, max_value=n_m, value=min(20, n_m), key="power_mach_slider")
                display_p_df = sorted_mach_power.head(show_p_count)
            else:
                display_p_df = sorted_mach_power

            fig_pw_mach = px.bar(
                display_p_df,
                x="Mean_Power_kW",
                y="Machine_Label",
                orientation="h",
                color="Mean_Power_kW",
                color_continuous_scale="Plasma",
                labels={"Mean_Power_kW": "Mean Power (kW)", "Machine_Label": "Machine"},
            )
            fig_pw_mach.update_layout(
                xaxis_title="Mean Electrical Power Demand (kW)",
                yaxis=dict(autorange="reversed"),
                margin=dict(l=60, r=20, t=20, b=40),
                height=max(320, len(display_p_df) * 18),
                coloraxis_showscale=False,
            )
            st.plotly_chart(fig_pw_mach, use_container_width=True)
            st.caption(
                f"Lowest mean power draw: **Machine {sorted_mach_power.iloc[0 if p_ascending else -1]['Machine_ID']}** "
                f"({sorted_mach_power.iloc[0 if p_ascending else -1]['Mean_Power_kW']:.2f} kW); "
                f"Highest mean power draw: **Machine {sorted_mach_power.iloc[-1 if p_ascending else 0]['Machine_ID']}** "
                f"({sorted_mach_power.iloc[-1 if p_ascending else 0]['Mean_Power_kW']:.2f} kW)."
            )

    with tab_pw_mode:
        st.markdown("##### Electrical Power Demand Across Operating Modes")
        if "Operation_Mode" in df.columns and "Power_Consumption_kW" in df.columns:
            fig_pw_mode = px.box(
                df,
                x="Operation_Mode",
                y="Power_Consumption_kW",
                color="Operation_Mode",
                color_discrete_map={"Active": "#1f77b4", "Idle": "#ff7f0e", "Maintenance": "#2ca02c"},
                labels={"Operation_Mode": "Operation Mode", "Power_Consumption_kW": "Power Consumption (kW)"},
            )
            fig_pw_mode.update_layout(
                xaxis_title="Operation Mode",
                yaxis_title="Power Consumption (kW)",
                margin=dict(l=40, r=20, t=20, b=40),
                height=320,
                showlegend=False,
            )
            st.plotly_chart(fig_pw_mode, use_container_width=True)

            if not mode_summary.empty:
                st.dataframe(
                    mode_summary[["Operation_Mode", "Record_Count", "Mean_Power_kW", "Std_Power_kW"]].rename(columns={
                        "Operation_Mode": "Mode",
                        "Record_Count": "Observations",
                        "Mean_Power_kW": "Mean Power (kW)",
                        "Std_Power_kW": "Power Std (kW)"
                    }),
                    use_container_width=True,
                    hide_index=True
                )
            st.caption(
                "Power consumption distributions are indistinguishable across Active, Idle, and Maintenance "
                "(all ~5.73 to 5.75 kW mean). Standby power reduction is not observed in this telemetry extract."
            )

    st.divider()

    # -----------------------------------------------------------------------
    # 4. Specific Energy Consumption (SEC) & Bivariate Dynamics (KPI 5)
    # -----------------------------------------------------------------------
    st.markdown("#### 3. Specific Energy Consumption (SEC) & Bivariate Dynamics")
    st.caption("Energy-adjusted production intensity evaluating row-level electrical energy per manufactured unit (kWh/unit).")

    # Formula callout
    st.markdown(
        r"$$\text{Specific Energy Consumption (SEC)} = \frac{\text{Power\_Consumption\_kW}}{\text{Production\_Speed\_units\_per\_hr}} \quad \left[\frac{\text{kW}}{\text{units/hr}} = \frac{\text{kWh}}{\text{unit}}\right]$$"
    )

    tab_sec_dist, tab_bivar, tab_sec_mach, tab_fleet_table = st.tabs([
        "⚡ SEC Distribution",
        "🎯 Speed vs. Power Dispersion",
        "🏆 Machine SEC Rankings",
        "📋 Fleet Summary Table"
    ])

    with tab_sec_dist:
        st.markdown("##### Row-Level Specific Energy Consumption (SEC) Distribution")
        # Compute row-level SEC series strictly for speed > 0
        if "Production_Speed_units_per_hr" in df.columns and "Power_Consumption_kW" in df.columns:
            pos_mask = df["Production_Speed_units_per_hr"] > 0
            eligible_count = int(pos_mask.sum())
            excluded_count = int((~pos_mask).sum())

            if eligible_count > 0:
                sec_series = df.loc[pos_mask, "Power_Consumption_kW"] / df.loc[pos_mask, "Production_Speed_units_per_hr"]
                sec_df = pd.DataFrame({"SEC_kWh_per_u": sec_series})
                if "Operation_Mode" in df.columns:
                    sec_df["Operation_Mode"] = df.loc[pos_mask, "Operation_Mode"].values

                fig_sec_hist = px.histogram(
                    sec_df,
                    x="SEC_kWh_per_u",
                    color="Operation_Mode" if "Operation_Mode" in sec_df.columns else None,
                    nbins=50,
                    barmode="overlay",
                    opacity=0.75,
                    labels={"SEC_kWh_per_u": "Specific Energy Consumption (kWh/unit)"},
                    color_discrete_map={"Active": "#1f77b4", "Idle": "#ff7f0e", "Maintenance": "#2ca02c"},
                )
                p50_sec = float(sec_series.median())
                p95_sec = float(np.percentile(sec_series, 95))
                fig_sec_hist.add_vline(
                    x=p50_sec,
                    line_dash="dash",
                    line_color="#2ca02c",
                    annotation_text=f"Median: {p50_sec:.4f} kWh/u",
                    annotation_position="top right",
                )
                fig_sec_hist.add_vline(
                    x=p95_sec,
                    line_dash="dot",
                    line_color="#d62728",
                    annotation_text=f"P95: {p95_sec:.4f} kWh/u",
                    annotation_position="top right",
                )
                fig_sec_hist.update_layout(
                    xaxis_title="Specific Energy Consumption (kWh/unit)",
                    yaxis_title="Observation Count",
                    margin=dict(l=40, r=20, t=30, b=40),
                    height=340,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                )
                st.plotly_chart(fig_sec_hist, use_container_width=True)
                st.caption(
                    f"Evaluated on **{eligible_count:,} eligible observations** (strictly speed > 0; **{excluded_count} excluded**). "
                    f"Mean SEC is **{sec_series.mean():.4f} kWh/unit** (Median: **{p50_sec:.4f}**, P95: **{p95_sec:.4f}**, "
                    f"Range: **[{sec_series.min():.4f}, {sec_series.max():.4f}] kWh/unit**). "
                    "The right-skewed profile reflects hyperbolic energy intensity when production speeds are low."
                )

    with tab_bivar:
        st.markdown("##### Production Speed vs. Electrical Power Demand Dispersion")
        st.caption("Bivariate operational space examining simultaneous throughput and power draw.")

        c_dec1, c_dec2 = st.columns(2)
        with c_dec1:
            decimation_option = st.selectbox(
                "Display Sample Size:",
                options=[1000, 2500, 5000, 10000, "All Records"],
                index=1,
                help="Decimate scatter plot points to preserve smooth browser rendering.",
                key="prod_bivar_decimate"
            )
        with c_dec2:
            color_choice = st.selectbox(
                "Color Dimension:",
                options=["Operation_Mode", "Efficiency_Status", "None"],
                index=0,
                key="prod_bivar_color"
            )

        # Apply decimation
        if decimation_option == "All Records" or len(df) <= int(decimation_option):
            scatter_df = df
            is_sampled = False
        else:
            sample_size = int(decimation_option)
            scatter_df = df.sample(n=sample_size, random_state=42)
            is_sampled = True

        color_col = None if color_choice == "None" else color_choice
        fig_bivar = px.scatter(
            scatter_df,
            x="Production_Speed_units_per_hr",
            y="Power_Consumption_kW",
            color=color_col if color_col in scatter_df.columns else None,
            opacity=0.6,
            labels={
                "Production_Speed_units_per_hr": "Production Speed (units/hr)",
                "Power_Consumption_kW": "Power Consumption (kW)",
            },
            color_discrete_map={
                "Active": "#1f77b4", "Idle": "#ff7f0e", "Maintenance": "#2ca02c",
                "Low": "#e6194b", "Medium": "#ffe119", "High": "#3cb44b"
            },
            hover_data=["Machine_ID", "Date"] if "Machine_ID" in scatter_df.columns else None,
        )
        fig_bivar.update_traces(marker=dict(size=5))
        fig_bivar.update_layout(
            xaxis_title="Production Speed (units/hr)",
            yaxis_title="Power Consumption (kW)",
            margin=dict(l=40, r=20, t=20, b=40),
            height=380,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig_bivar, use_container_width=True)

        corr_val = df[["Production_Speed_units_per_hr", "Power_Consumption_kW"]].dropna().corr().iloc[0, 1] if len(df) > 1 else 0.0
        sample_note = f" (Displaying random sample of {len(scatter_df):,} records)" if is_sampled else ""
        st.caption(
            f"Pearson linear correlation between Production Speed and Power Consumption: **r = {corr_val:.4f}**{sample_note}. "
            "Zero linear correlation indicates that electrical power draw is statistically decoupled from production speed in this dataset."
        )

    with tab_sec_mach:
        st.markdown("##### Machine Energy Intensity Rankings (SEC in kWh/unit)")
        if not prod_energy_summary.empty:
            n_m = len(prod_energy_summary)
            c_sec1, c_sec2 = st.columns([2, 1])
            with c_sec2:
                sort_sec_order = st.radio(
                    "Sort By SEC:",
                    options=["Lowest to Highest (Most Efficient)", "Highest to Lowest"],
                    index=0,
                    horizontal=True,
                    key="sort_sec_order"
                )
            
            sec_ascending = (sort_sec_order == "Lowest to Highest (Most Efficient)")
            sorted_mach_sec = prod_energy_summary.sort_values(by="Mean_SEC_kWh_per_u", ascending=sec_ascending).copy()
            sorted_mach_sec["Machine_Label"] = sorted_mach_sec["Machine_ID"].apply(lambda m: f"Machine {m}")

            if n_m > 10:
                show_sec_count = st.slider("Machines to Display:", min_value=5, max_value=n_m, value=min(20, n_m), key="sec_mach_slider")
                display_sec_df = sorted_mach_sec.head(show_sec_count)
            else:
                display_sec_df = sorted_mach_sec

            fig_sec_mach = px.bar(
                display_sec_df,
                x="Mean_SEC_kWh_per_u",
                y="Machine_Label",
                orientation="h",
                color="Mean_SEC_kWh_per_u",
                color_continuous_scale="Tealgrn",
                labels={"Mean_SEC_kWh_per_u": "Mean SEC (kWh/unit)", "Machine_Label": "Machine"},
            )
            fig_sec_mach.update_layout(
                xaxis_title="Specific Energy Consumption (kWh/unit)",
                yaxis=dict(autorange="reversed"),
                margin=dict(l=60, r=20, t=20, b=40),
                height=max(320, len(display_sec_df) * 18),
                coloraxis_showscale=False,
            )
            st.plotly_chart(fig_sec_mach, use_container_width=True)
            st.caption(
                f"Most energy-efficient machine: **Machine {sorted_mach_sec.iloc[0 if sec_ascending else -1]['Machine_ID']}** "
                f"({sorted_mach_sec.iloc[0 if sec_ascending else -1]['Mean_SEC_kWh_per_u']:.4f} kWh/u); "
                f"Highest intensity machine: **Machine {sorted_mach_sec.iloc[-1 if sec_ascending else 0]['Machine_ID']}** "
                f"({sorted_mach_sec.iloc[-1 if sec_ascending else 0]['Mean_SEC_kWh_per_u']:.4f} kWh/u)."
            )

    with tab_fleet_table:
        st.markdown("##### Machine Fleet Production & Energy Summary Table")
        if not prod_energy_summary.empty:
            fmt_table = prod_energy_summary.copy()
            fmt_table = fmt_table.rename(columns={
                "Machine_ID": "Machine",
                "Record_Count": "Records",
                "Mean_Speed_u_per_hr": "Speed Mean (u/hr)",
                "Median_Speed_u_per_hr": "Speed Med (u/hr)",
                "Mean_Power_kW": "Power Mean (kW)",
                "Median_Power_kW": "Power Med (kW)",
                "Mean_SEC_kWh_per_u": "SEC Mean (kWh/u)",
                "Speed_Rank": "Speed Rank",
                "Power_Rank": "Power Rank",
                "SEC_Rank": "SEC Rank",
            })
            st.dataframe(
                fmt_table[["Machine", "Records", "Speed Mean (u/hr)", "Speed Med (u/hr)", "Power Mean (kW)", "Power Med (kW)", "SEC Mean (kWh/u)", "Speed Rank", "Power Rank", "SEC Rank"]],
                use_container_width=True,
                hide_index=True
            )
