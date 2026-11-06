r"""
Module 4: Quality Assurance & Efficiency Diagnostics.
Manufacturing Diagnostic Intelligence System - Phase 2.3.

Target Diagnostic Pillar:
- Product Quality & Quality Assurance (KPI 3).
- Operational Efficiency & Energy-Adjusted Intensity (KPI 5).

Responsibilities:
- Surfaces finished-good defect rates (`Quality_Control_Defect_Rate_%`).
- Reports the arithmetic complement ($94.991194\%$) with mandatory yield disclaimers.
- Tracks process execution error rates (`Error_Rate_%`) as a separate diagnostic channel.
- Evaluates Specific Energy Consumption (SEC) strictly at row-level for positive speeds.
- Reports empirical category breakdowns for recorded `Efficiency_Status` labels.
- Preserves original classification labels and documents the 2 boundary mismatches at 5.0%.
- Houses functional layout shells for Phase 2.5 defect Pareto charts and contingency matrices.
"""

from __future__ import annotations

from typing import Any, Dict

import pandas as pd
import streamlit as st

from scripts.app.components import render_empty_state, render_kpi_card, render_section_header


def render_quality_efficiency(df: pd.DataFrame, kpis: Dict[str, Any]) -> None:
    """
    Render Module 4: Quality Assurance & Efficiency Diagnostics shell.

    Parameters:
        df: Filtered or full DataFrame slice for quality and efficiency diagnostics.
        kpis: Pre-calculated KPI dictionary from kpi_engine.calculate_all_kpis().
    """
    render_section_header(
        title="Module 4: Quality Assurance & Efficiency Diagnostics",
        description="Quality defect rates, process error telemetry, specific energy consumption (SEC), and multi-tier efficiency ratings.",
    )

    if df.empty:
        render_empty_state(
            title="No Quality or Efficiency Telemetry",
            message="No records match your active filter selection.",
            suggestion="Adjust your sidebar filters to include more machines or operation modes."
        )
        return

    pq = kpis.get("product_quality", {})
    defect = pq.get("defect_rate", {})
    comp = pq.get("arithmetic_complement", {})
    error = pq.get("process_error_rate", {})

    ee = kpis.get("energy_efficiency", {})
    sec = ee.get("specific_energy_consumption", {})
    status_info = ee.get("efficiency_status_breakdown", {})
    status_counts = status_info.get("counts", {})
    status_pcts = status_info.get("percentages", {})

    # Top-Level Quality & Efficiency Indicators
    st.markdown("#### Quality & Specific Energy Consumption (KPI 3 & KPI 5)")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        render_kpi_card(
            label="Mean Defect Rate",
            value=defect.get("mean", 0.0),
            unit="%",
            subtext=f"Median: {defect.get('median', 0.0):.2f}% | P95: {defect.get('p95', 0.0):.2f}%",
            help_text="Finished-good quality inspection defect percentage."
        )

    with col2:
        render_kpi_card(
            label="Arithmetic Complement",
            value=comp.get("value", 0.0),
            unit="%",
            subtext="100 - Mean Defect Rate (%)",
            help_text="Strictly the arithmetic complement of the recorded mean defect rate. Not verified yield."
        )

    with col3:
        render_kpi_card(
            label="Process Error Rate",
            value=error.get("mean", 0.0),
            unit="%",
            subtext=f"Median: {error.get('median', 0.0):.2f}% | P95: {error.get('p95', 0.0):.2f}%",
            help_text="Machine controller execution and process error rate."
        )

    with col4:
        render_kpi_card(
            label="Mean SEC",
            value=sec.get("mean", 0.0),
            unit="kWh/unit",
            subtext=f"Eligible: {sec.get('eligible_count', 0):,} records",
            help_text="Specific Energy Consumption evaluated row-level for positive production speeds."
        )

    # Efficiency Status Empirical Breakdown
    st.markdown("#### Empirical Efficiency Status Breakdown")
    st.caption("Recorded categorization across Low, Medium, and High efficiency classes:")
    sc1, sc2, sc3 = st.columns(3)
    with sc1:
        render_kpi_card(
            label="Low Efficiency",
            value=status_counts.get("Low", 0),
            unit="records",
            subtext=f"{status_pcts.get('Low', 0.0):.2f}% of fleet observations",
        )
    with sc2:
        render_kpi_card(
            label="Medium Efficiency",
            value=status_counts.get("Medium", 0),
            unit="records",
            subtext=f"{status_pcts.get('Medium', 0.0):.2f}% of fleet observations",
        )
    with sc3:
        render_kpi_card(
            label="High Efficiency",
            value=status_counts.get("High", 0),
            unit="records",
            subtext=f"{status_pcts.get('High', 0.0):.2f}% of fleet observations",
        )

    # Architectural Safeguard Notice
    st.info(
        r"**Provisional Safeguard Notice:** The arithmetic complement ($94.991194\%$) is strictly $100 - \text{mean defect rate}$. "
        r"It must NOT be presented as verified first-pass yield, product conformance, or process capability. "
        r"The recorded Efficiency_Status labels are preserved without reconstruction; exactly two candidate classification "
        r"mismatches exist at $\text{Error\_Rate\_\%} = 5.0\%$."
    )

    # Functional Shell Containers for Phase 2.5 Visual Analytics
    st.markdown("#### Diagnostic Visualization Shells")
    c1, c2 = st.columns(2)
    with c1:
        with st.container(border=True):
            st.markdown("##### Defect vs. Error Rate Stratification")
            st.caption("Target Phase 2.5 deliverable: Interactive bivariate quality vs. process execution error analysis.")
            st.info("Interactive defect vs. error decile visualizer scheduled for implementation in Phase 2.5.")
    with c2:
        with st.container(border=True):
            st.markdown("##### Efficiency Status Contingency & SEC Distributions")
            st.caption("Target Phase 2.5 deliverable: Specific Energy Consumption density curves by efficiency tier.")
            st.info("Interactive SEC distribution and contingency heatmap scheduled for implementation in Phase 2.5.")

