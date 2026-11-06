"""
Manufacturing Diagnostic Intelligence System.
Phase 2.3 — Streamlit Dashboard Shell & Navigation Framework.

This module serves as the primary application entry point for the Streamlit dashboard:
- Configures page title, layout, icon, and sidebar navigation state.
- Ingests telemetry via the Phase 2.1.2 Data Access Engine (scripts/app/data_loader.py).
- Evaluates strategic KPI domains via the Phase 2.2 KPI Engine (scripts/app/kpi_engine.py).
- Provides global sidebar filters (Operation Mode, Machine ID, Date Range).
- Houses functional navigation between the four approved dashboard modules:
    Module 1: Factory Health & Network Overview
    Module 2: Machine Health & Condition Monitoring
    Module 3: Production Throughput & Energy Monitoring
    Module 4: Quality Assurance & Efficiency Diagnostics
- Handles loading and validation errors gracefully with defensive error boundaries.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Callable, Dict, Tuple

import pandas as pd
import streamlit as st

# Ensure project root is present in sys.path for direct imports
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.app.components import (
    apply_filters,
    render_empty_state,
    render_error_state,
    render_filter_sidebar,
)
from scripts.app.data_loader import (
    DataLoaderError,
    load_manufacturing_data,
)
from scripts.app.kpi_engine import (
    KPIEngineError,
    calculate_all_kpis,
)
from scripts.app.modules.factory_overview import render_factory_overview
from scripts.app.modules.machine_health import render_machine_health
from scripts.app.modules.production_energy import render_production_energy
from scripts.app.modules.quality_efficiency import render_quality_efficiency


# ---------------------------------------------------------------------------
# Module Registry Configuration
# ---------------------------------------------------------------------------

MODULE_REGISTRY: Dict[str, Dict[str, Any]] = {
    "factory_overview": {
        "index": 1,
        "name": "Module 1: Factory Health & Network Overview",
        "short_name": "Factory Health & Network",
        "pillar": "Fleet Telemetry & 6G QoS Surveillance (KPI 4)",
        "render_fn": render_factory_overview,
    },
    "machine_health": {
        "index": 2,
        "name": "Module 2: Machine Health & Condition Monitoring",
        "short_name": "Machine Health & Condition",
        "pillar": "Mechanical Health & Degradation Indicators (KPI 1)",
        "render_fn": render_machine_health,
    },
    "production_energy": {
        "index": 3,
        "name": "Module 3: Production Throughput & Energy Monitoring",
        "short_name": "Production & Energy",
        "pillar": "Fleet Throughput & Power Demand Baselines (KPI 2)",
        "render_fn": render_production_energy,
    },
    "quality_efficiency": {
        "index": 4,
        "name": "Module 4: Quality Assurance & Efficiency Diagnostics",
        "short_name": "Quality & Efficiency",
        "pillar": "Defect Rates, SEC Intensity & Efficiency Tiers (KPI 3 & 5)",
        "render_fn": render_quality_efficiency,
    },
}


# ---------------------------------------------------------------------------
# Cached Ingestion and Calculation Pipelines
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def load_application_data() -> pd.DataFrame:
    """
    Ingest and validate the manufacturing dataset via the Phase 2.1.2 data loader.

    Returns:
        Validated in-memory pandas DataFrame.
    """
    return load_manufacturing_data(validate=True, add_parsed_datetime=True)


@st.cache_data(show_spinner=False)
def compute_application_kpis(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Evaluate the five strategic KPI domains via the Phase 2.2 KPI engine.

    Returns:
        Structured dictionary containing results for all five KPI domains.
    """
    return calculate_all_kpis(df)


# ---------------------------------------------------------------------------
# Primary Application Entrypoint
# ---------------------------------------------------------------------------

def main() -> None:
    """Initialize and run the Streamlit dashboard shell."""
    st.set_page_config(
        page_title="Manufacturing Diagnostic Intelligence System",
        page_icon="🏭",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Application Header
    st.title("🏭 Manufacturing Diagnostic Intelligence System")
    st.caption(
        "6G-Enabled Smart Factory Process Health, Operational Throughput, Quality Conformance & Energy Diagnostics"
    )

    # 1. Ingest Data via Data Access Engine
    try:
        df_raw = load_application_data()
    except DataLoaderError as err:
        render_error_state(
            title="Data Access Layer Failure",
            message="The core data loader failed to validate the manufacturing dataset schema or checksum.",
            exception=err,
        )
        return
    except Exception as exc:
        render_error_state(
            title="Unexpected Data Ingestion Error",
            message="An unexpected error occurred while loading the source telemetry dataset.",
            exception=exc,
        )
        return

    # 2. Render Sidebar Navigation & Filters
    st.sidebar.title("Navigation")
    module_keys = list(MODULE_REGISTRY.keys())
    module_labels = [MODULE_REGISTRY[k]["name"] for k in module_keys]

    selected_label = st.sidebar.radio(
        "Select Diagnostic Module:",
        options=module_labels,
        index=0,
        help="Switch between the four approved analytical modules.",
    )

    # Resolve active module key
    active_key = module_keys[module_labels.index(selected_label)]
    active_module = MODULE_REGISTRY[active_key]

    st.sidebar.divider()

    # Render Reusable Sidebar Filters
    active_filters = render_filter_sidebar(df_raw)
    df_filtered = apply_filters(df_raw, active_filters)

    # Telemetry Status Widget in Sidebar
    st.sidebar.divider()
    st.sidebar.markdown(f"**Dataset Status:** Active ({len(df_filtered):,} / {len(df_raw):,} records)")
    st.sidebar.caption("Source SHA-256: `060052A2...88AF` (Verified)")

    # 3. Compute KPIs via KPI Engine
    if df_filtered.empty:
        render_empty_state(
            title="No Records Match Selected Filters",
            message="Your current filter parameters yielded 0 observations.",
            suggestion="Adjust operation modes, select more machines, or widen your date range in the sidebar.",
        )
        return

    try:
        kpi_results = compute_application_kpis(df_filtered)
    except KPIEngineError as kerr:
        render_error_state(
            title="KPI Calculation Engine Error",
            message="The KPI calculation engine failed on the filtered dataset slice.",
            exception=kerr,
        )
        return
    except Exception as exc:
        render_error_state(
            title="Unexpected KPI Evaluation Error",
            message="An unexpected error occurred during KPI computation.",
            exception=exc,
        )
        return

    # 4. Dispatch to Selected Module Entrypoint
    render_fn: Callable[[pd.DataFrame, Dict[str, Any]], None] = active_module["render_fn"]
    render_fn(df_filtered, kpi_results)


if __name__ == "__main__":
    main()

