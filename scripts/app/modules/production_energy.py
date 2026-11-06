"""
Module 3: Production Throughput & Energy Monitoring.
Manufacturing Diagnostic Intelligence System - Phase 2.3.

Target Diagnostic Pillar:
- Production Performance & Fleet Throughput (KPI 2).
- Operational Mode Allocations & Electrical Power Demand Baselines.

Responsibilities:
- Surfaces fleet-wide throughput across all three operation modes (Active, Idle, Maintenance).
- Presents mode-stratified throughput rates in units/hr.
- Tracks electrical power consumption baselines.
- Strictly enforces capacity utilization safeguards (no unverified nameplate capacity assumptions).
- Houses functional layout shells for Phase 2.5 speed distributions and energy demand timelines.
"""

from __future__ import annotations

from typing import Any, Dict

import pandas as pd
import streamlit as st

from scripts.app.components import render_empty_state, render_kpi_card, render_section_header


def render_production_energy(df: pd.DataFrame, kpis: Dict[str, Any]) -> None:
    """
    Render Module 3: Production Throughput & Energy Monitoring shell.

    Parameters:
        df: Filtered or full DataFrame slice for throughput and energy monitoring.
        kpis: Pre-calculated KPI dictionary from kpi_engine.calculate_all_kpis().
    """
    render_section_header(
        title="Module 3: Production Throughput & Energy Monitoring",
        description="Fleet throughput rates, operational mode allocations, power demand, and energy intensity baselines.",
    )

    if df.empty:
        render_empty_state(
            title="No Production Data Found",
            message="No records match your active filter selection.",
            suggestion="Adjust your sidebar filters to include more machines or operation modes."
        )
        return

    otr = kpis.get("operational_throughput", {})
    fleet = otr.get("fleet_throughput", {})
    modes = otr.get("mode_stratified_throughput", {})

    # Top-Level Throughput Cards
    st.markdown("#### Operational Throughput Rate Indicators (KPI 2)")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        render_kpi_card(
            label="Fleet Mean Speed",
            value=fleet.get("mean", 0.0),
            unit="units/hr",
            subtext=f"Median: {fleet.get('median', 0.0):.1f} u/hr | P95: {fleet.get('p95', 0.0):.1f} u/hr",
            help_text="Fleet-wide empirical manufacturing throughput rate across all operation modes."
        )

    with col2:
        active_stats = modes.get("Active", {})
        render_kpi_card(
            label="Active Mode Speed",
            value=active_stats.get("mean", 0.0),
            unit="units/hr",
            subtext=f"Count: {active_stats.get('count', 0):,} records",
            help_text="Mean production throughput while tagged in Active operation mode."
        )

    with col3:
        idle_stats = modes.get("Idle", {})
        render_kpi_card(
            label="Idle Mode Speed",
            value=idle_stats.get("mean", 0.0),
            unit="units/hr",
            subtext=f"Count: {idle_stats.get('count', 0):,} records",
            help_text="Mean production throughput while tagged in Idle operation mode."
        )

    with col4:
        maint_stats = modes.get("Maintenance", {})
        render_kpi_card(
            label="Maintenance Speed",
            value=maint_stats.get("mean", 0.0),
            unit="units/hr",
            subtext=f"Count: {maint_stats.get('count', 0):,} records",
            help_text="Mean production throughput while tagged in Maintenance operation mode."
        )

    # Architectural Safeguard Notice
    st.info(
        "**Provisional Safeguard Notice:** Throughput is reported strictly as empirical production speed in units/hr. "
        "The observed sample maximum (~500 units/hr) is NOT treated as rated machine capacity. Capacity utilization "
        "percentages and production quotas remain uncalculated pending manufacturer nameplate specifications."
    )

    # Functional Shell Containers for Phase 2.5 Visual Analytics
    st.markdown("#### Diagnostic Visualization Shells")
    c1, c2 = st.columns(2)
    with c1:
        with st.container(border=True):
            st.markdown("##### Production Speed vs. Electrical Power Distribution")
            st.caption("Target Phase 2.5 deliverable: Scatter and regression analysis of power demand across operation modes.")
            st.info("Interactive power vs. speed bivariate visualizer scheduled for implementation in Phase 2.5.")
    with c2:
        with st.container(border=True):
            st.markdown("##### Temporal Production & Power Demand Timeline")
            st.caption("Target Phase 2.5 deliverable: Diurnal and longitudinal throughput dynamics across 69 calendar dates.")
            st.info("Interactive daily throughput and energy timeline scheduled for implementation in Phase 2.5.")

