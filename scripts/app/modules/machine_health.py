"""
Module 2: Machine Health & Condition Monitoring.
Manufacturing Diagnostic Intelligence System - Phase 2.3.

Target Diagnostic Pillar:
- Machine Health & Mechanical Condition Surveillance (KPI 1).

Responsibilities:
- Surfaces thermal bearing/core conditions (`Temperature_C`).
- Monitors mechanical oscillation frequencies (`Vibration_Hz`).
- Tracks algorithmic degradation scores (`Predictive_Maintenance_Score`).
- Strictly enforces separate unweighted indicators (no composite Machine Health Index).
- Preserves neutral reporting of PM score polarity (unresolved directionality).
- Houses functional layout shells for Phase 2.4 bivariate scatter plots and temporal degradation curves.
"""

from __future__ import annotations

from typing import Any, Dict

import pandas as pd
import streamlit as st

from scripts.app.components import render_empty_state, render_kpi_card, render_section_header


def render_machine_health(df: pd.DataFrame, kpis: Dict[str, Any]) -> None:
    """
    Render Module 2: Machine Health & Condition Monitoring shell.

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
            message="No observations match your active filter selection.",
            suggestion="Adjust your sidebar filters to include more machines or operation modes."
        )
        return

    mh = kpis.get("machine_health", {})
    temp = mh.get("temperature_c", {})
    vib = mh.get("vibration_hz", {})
    pm = mh.get("predictive_maintenance_score", {})

    # Top-Level Health Indicator Cards (Separate, Unweighted)
    st.markdown("#### Independent Mechanical Condition Indicators (KPI 1)")
    col1, col2, col3 = st.columns(3)

    with col1:
        render_kpi_card(
            label="Mean Core Temperature",
            value=temp.get("mean", 0.0),
            unit="°C",
            subtext=f"Median: {temp.get('median', 0.0):.2f} °C | Range: [{temp.get('min', 0.0):.1f}, {temp.get('max', 0.0):.1f}] °C",
            help_text="Thermal measurement of machinery core and bearing telemetry."
        )

    with col2:
        render_kpi_card(
            label="Mean Mechanical Vibration",
            value=vib.get("mean", 0.0),
            unit="Hz",
            subtext=f"Median: {vib.get('median', 0.0):.2f} Hz | P95: {vib.get('p95', 0.0):.2f} Hz",
            help_text="Mechanical oscillation frequency telemetry."
        )

    with col3:
        render_kpi_card(
            label="Predictive Maintenance Score",
            value=pm.get("mean", 0.0),
            unit="score",
            subtext=f"Median: {pm.get('median', 0.0):.2f} | Polarity: Neutral Unresolved",
            help_text="Normalized algorithmic health indicator [0.0, 1.0]. Directionality is unverified."
        )

    # Architectural Safeguard Notice
    st.info(
        "**Provisional Safeguard Notice:** Raw temperature, vibration, and predictive maintenance scores are tracked "
        "as separate, unweighted, independent indicators. No composite 'Machine Health Index' is computed without "
        "approved normalization baselines and confirmed PM score polarity ($0.0 = \\text{healthy}$ vs. $1.0 = \\text{healthy}$)."
    )

    # Functional Shell Containers for Phase 2.4 Visual Analytics
    st.markdown("#### Diagnostic Visualization Shells")
    c1, c2 = st.columns(2)
    with c1:
        with st.container(border=True):
            st.markdown("##### Thermal vs. Vibration Bivariate Dispersion")
            st.caption("Target Phase 2.4 deliverable: Interactive multi-axis mechanical correlation scatter plots.")
            st.info("Bivariate mechanical surveillance scatter visualizer scheduled for implementation in Phase 2.4.")
    with c2:
        with st.container(border=True):
            st.markdown("##### Machine Health Telemetry Profiles")
            st.caption("Target Phase 2.4 deliverable: Machine-specific sensor time series across 50 manufacturing units.")
            st.info("Longitudinal machine condition profile visualizer scheduled for implementation in Phase 2.4.")

