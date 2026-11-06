"""
Reusable UI Components and Filter Utilities for Streamlit Dashboard.
Manufacturing Diagnostic Intelligence System - Phase 2.3.

This module provides standardized, modular presentation components and filter
utilities for the multi-module dashboard shell:
- Standardized KPI metric cards.
- Section headers with consistent typography.
- Graceful error states and empty states.
- Reusable sidebar filter controls.
- Deterministic, non-mutating DataFrame filtering.

Design Principles:
- Reusable across all four dashboard modules.
- Does NOT duplicate calculation logic (strictly consumes kpi_engine outputs).
- Defensive against empty, null, or out-of-range inputs.
- Pure headless compatibility with Streamlit's AppTest harness.
"""

from __future__ import annotations

import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

import pandas as pd
import streamlit as st


# ---------------------------------------------------------------------------
# Section Headers and Typography
# ---------------------------------------------------------------------------

def render_section_header(
    title: str,
    description: Optional[str] = None,
    divider: bool = True
) -> None:
    """
    Render a standardized section header with title, optional description, and divider.

    Parameters:
        title: Header title text.
        description: Optional explanatory subtext.
        divider: Whether to append a horizontal divider rule.
    """
    st.subheader(title)
    if description:
        st.markdown(f"*{description}*")
    if divider:
        st.divider()


# ---------------------------------------------------------------------------
# Standardized KPI Metric Cards
# ---------------------------------------------------------------------------

def render_kpi_card(
    label: str,
    value: Union[int, float, str],
    unit: str = "",
    delta: Optional[str] = None,
    subtext: Optional[str] = None,
    help_text: Optional[str] = None
) -> None:
    """
    Render a standardized KPI card displaying metric value, unit, and optional subtext.

    Parameters:
        label: Descriptive metric label.
        value: Numeric or formatted string value.
        unit: Measurement unit (e.g., '°C', 'Hz', 'units/hr', 'ms', '%', 'kWh/unit').
        delta: Optional change or status indicator string.
        subtext: Optional explanatory footnote or caveat.
        help_text: Tooltip help text for metric definition.
    """
    if isinstance(value, float):
        # Format floating-point values cleanly
        if abs(value) >= 1000:
            formatted_val = f"{value:,.2f}"
        elif abs(value) >= 1:
            formatted_val = f"{value:.4f}"
        else:
            formatted_val = f"{value:.6f}"
    elif isinstance(value, int):
        formatted_val = f"{value:,}"
    else:
        formatted_val = str(value)

    display_val = f"{formatted_val} {unit}".strip() if unit else formatted_val

    st.metric(
        label=label,
        value=display_val,
        delta=delta,
        help=help_text,
    )
    if subtext:
        st.caption(subtext)


# ---------------------------------------------------------------------------
# Error and Empty States
# ---------------------------------------------------------------------------

def render_error_state(
    title: str,
    message: str,
    exception: Optional[Exception] = None
) -> None:
    """
    Render an informative, user-friendly error state with diagnostic guidance.

    Parameters:
        title: Summary of the error condition.
        message: Operational guidance or cause explanation.
        exception: Optional underlying exception object for technical details.
    """
    st.error(f"**{title}**\n\n{message}")
    if exception is not None:
        with st.expander("Technical Diagnostic Details"):
            st.code(f"{type(exception).__name__}: {str(exception)}")


def render_empty_state(
    title: str = "No Data Available",
    message: str = "No records match the current filter selection.",
    suggestion: Optional[str] = "Try widening your date range, adding more operation modes, or selecting all machines."
) -> None:
    """
    Render an informative empty state when filtered datasets return zero records.

    Parameters:
        title: Heading for the empty state notice.
        message: Description of the empty condition.
        suggestion: Actionable advice for recovering data.
    """
    st.warning(f"**{title}**\n\n{message}")
    if suggestion:
        st.info(f"**Suggestion:** {suggestion}")


# ---------------------------------------------------------------------------
# Sidebar Filters and Filtering Logic
# ---------------------------------------------------------------------------

def render_filter_sidebar(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Render global filter controls in the Streamlit sidebar.

    Filters provided:
    1. Operation Mode multi-select (Active, Idle, Maintenance).
    2. Machine ID multi-select (1 to 50).
    3. Date Range picker (bounded by min and max dates in dataset).

    Parameters:
        df: Input DataFrame containing 'Operation_Mode', 'Machine_ID', and 'datetime' or 'Date'.

    Returns:
        Dictionary of active filter parameters.
    """
    st.sidebar.markdown("### Global Filters")
    st.sidebar.caption("Filter telemetry across all dashboard modules.")

    # 1. Operation Mode Filter
    available_modes = sorted(list(df["Operation_Mode"].unique()))
    selected_modes = st.sidebar.multiselect(
        "Operation Mode",
        options=available_modes,
        default=available_modes,
        help="Filter telemetry by recorded operational state."
    )

    # 2. Machine ID Filter
    available_machines = sorted([int(m) for m in df["Machine_ID"].unique()])
    select_all_machines = st.sidebar.checkbox("Select All Machines", value=True)
    
    if select_all_machines:
        selected_machines = available_machines
    else:
        selected_machines = st.sidebar.multiselect(
            "Machine ID",
            options=available_machines,
            default=available_machines[:5],
            help="Select one or more machine identifiers (1 to 50)."
        )

    # 3. Date Range Filter
    if "datetime" in df.columns and pd.api.types.is_datetime64_any_dtype(df["datetime"]):
        min_date = df["datetime"].dt.date.min()
        max_date = df["datetime"].dt.date.max()
    else:
        # Fallback date parsing if datetime column not present
        parsed_dates = pd.to_datetime(df["Date"], format="%d-%m-%Y", errors="coerce").dt.date
        min_date = parsed_dates.min()
        max_date = parsed_dates.max()

    selected_date_range = st.sidebar.date_input(
        "Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        help="Select observation window between 01-01-2025 and 10-03-2025."
    )

    return {
        "selected_modes": selected_modes,
        "selected_machines": selected_machines,
        "date_range": selected_date_range,
    }


def apply_filters(df: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
    """
    Apply filter criteria to a DataFrame without mutating the original object.

    Parameters:
        df: Source DataFrame.
        filters: Filter dictionary produced by render_filter_sidebar, or custom test dict.

    Returns:
        Filtered pandas DataFrame slice.
    """
    filtered = df.copy()

    # 1. Filter Operation Modes
    # Supports 'selected_modes', 'operation_modes', or 'operation_mode'
    modes = filters.get("selected_modes")
    if modes is None:
        modes = filters.get("operation_modes")
    if modes is None and "operation_mode" in filters:
        op_val = filters["operation_mode"]
        modes = [op_val] if isinstance(op_val, str) else op_val

    if modes is not None:
        if isinstance(modes, str):
            modes = [modes]
        if len(modes) == 0:
            return filtered.iloc[0:0]
        filtered = filtered[filtered["Operation_Mode"].isin(modes)]

    # 2. Filter Machine IDs
    # Supports 'selected_machines', 'machine_ids', or 'machine_id'
    machines = filters.get("selected_machines")
    if machines is None:
        machines = filters.get("machine_ids")
    if machines is None and "machine_id" in filters:
        m_val = filters["machine_id"]
        machines = [m_val] if isinstance(m_val, (int, str)) else m_val

    if machines is not None:
        if isinstance(machines, (int, str)):
            machines = [machines]
        if len(machines) == 0:
            return filtered.iloc[0:0]
        filtered = filtered[filtered["Machine_ID"].isin(machines)]

    # 3. Filter Date Range
    date_range = filters.get("date_range")
    if date_range and isinstance(date_range, (tuple, list)) and len(date_range) == 2:
        start_date, end_date = date_range
        if start_date and end_date:
            if "datetime" in filtered.columns and pd.api.types.is_datetime64_any_dtype(filtered["datetime"]):
                date_mask = (filtered["datetime"].dt.date >= start_date) & (filtered["datetime"].dt.date <= end_date)
            else:
                dt_series = pd.to_datetime(filtered["Date"], format="%d-%m-%Y", errors="coerce").dt.date
                date_mask = (dt_series >= start_date) & (dt_series <= end_date)
            filtered = filtered[date_mask]

    return filtered

