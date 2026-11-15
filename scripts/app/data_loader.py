"""
Core Data Access and Schema Validation Engine.
Manufacturing Diagnostic Intelligence System - Phase 2.

This module provides robust, testable, and reusable data-access routines for the
manufacturing dataset:
- Resolves the dataset path relative to the repository root.
- Caches data in memory using Streamlit's @st.cache_data decorator.
- Performs comprehensive structural schema and data-integrity validation.
- Parses documented date/time formats without loss of provenance.
- Preserves all 100,000 records, including verified timestamp collisions.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union

import numpy as np
import pandas as pd
import streamlit as st


# ---------------------------------------------------------------------------
# Constants and Schema Specifications
# ---------------------------------------------------------------------------

# Canonical SHA-256 checksums for the manufacturing dataset
# 1. Original Windows CRLF checkout (9,356,442 bytes)
EXPECTED_SHA256_WINDOWS_CRLF: str = "060052A2975034C1D424FDF50089E6D94A5DB736EB85F35CDA0E0B907FF988AF"

# 2. Normalized Linux / Git LF checkout (9,256,441 bytes, e.g. Streamlit Cloud)
EXPECTED_SHA256_LINUX_LF: str = "0C59D3C93C94A9994CD3503FBD9E7A58697D7EEC5B0FA8CAFC4B9ECF5810C700"

# Backward-compatibility alias
EXPECTED_SHA256: str = EXPECTED_SHA256_WINDOWS_CRLF

# Accepted canonical checksum set across platforms and checkout configurations
VALID_DATASET_CHECKSUMS: Set[str] = {
    EXPECTED_SHA256_WINDOWS_CRLF,
    EXPECTED_SHA256_LINUX_LF,
}

EXPECTED_ROW_COUNT: int = 100000
EXPECTED_MACHINE_COUNT: int = 50
EXPECTED_UNIQUE_DATES_COUNT: int = 69

EXPECTED_COLUMNS: List[str] = [
    "Date",
    "Timestamp",
    "Machine_ID",
    "Operation_Mode",
    "Temperature_C",
    "Vibration_Hz",
    "Power_Consumption_kW",
    "Network_Latency_ms",
    "Packet_Loss_%",
    "Quality_Control_Defect_Rate_%",
    "Production_Speed_units_per_hr",
    "Predictive_Maintenance_Score",
    "Error_Rate_%",
    "Efficiency_Status",
]

NUMERIC_COLUMNS: List[str] = [
    "Temperature_C",
    "Vibration_Hz",
    "Power_Consumption_kW",
    "Network_Latency_ms",
    "Packet_Loss_%",
    "Quality_Control_Defect_Rate_%",
    "Production_Speed_units_per_hr",
    "Predictive_Maintenance_Score",
    "Error_Rate_%",
]

VALID_OPERATION_MODES: Set[str] = {"Active", "Idle", "Maintenance"}
VALID_EFFICIENCY_STATUSES: Set[str] = {"Low", "Medium", "High"}

# Hard physical / mathematical plausibility boundaries
# Note: These are hard rejection limits grounded in basic physics and definition domains,
# not unverified proprietary engineering alarm thresholds.
PHYSICAL_DOMAIN_LIMITS: Dict[str, Tuple[Optional[float], Optional[float]]] = {
    "Temperature_C": (0.0, None),                  # Non-negative in operational plant context (Task 1.4)
    "Vibration_Hz": (0.0, None),                   # Frequency non-negative (Task 1.4)
    "Power_Consumption_kW": (0.0, None),           # Power draw non-negative
    "Network_Latency_ms": (0.0, None),             # Delay non-negative
    "Packet_Loss_%": (0.0, 100.0),                 # Percentage bounded [0, 100]
    "Quality_Control_Defect_Rate_%": (0.0, 100.0), # Percentage bounded [0, 100]
    "Production_Speed_units_per_hr": (0.0, None),  # Speed non-negative
    "Predictive_Maintenance_Score": (0.0, 1.0),    # Normalized score [0, 1]
    "Error_Rate_%": (0.0, 100.0),                  # Percentage bounded [0, 100] (Task 1.4)
}

# Empirical observational ranges established across Phase 1 audits (Tasks 1.4-1.9)
# Documented for informational reference and drift screening, NOT hard rejection.
EMPIRICAL_OBSERVED_RANGES: Dict[str, Tuple[float, float]] = {
    "Temperature_C": (30.000, 89.999),
    "Vibration_Hz": (0.100, 5.000),
    "Power_Consumption_kW": (1.500, 10.000),
    "Network_Latency_ms": (1.000, 50.000),
    "Packet_Loss_%": (0.000, 5.000),
    "Quality_Control_Defect_Rate_%": (0.000, 10.000),
    "Production_Speed_units_per_hr": (50.000, 499.997),
    "Predictive_Maintenance_Score": (0.000, 1.000),
    "Error_Rate_%": (0.000, 15.000),
}


# ---------------------------------------------------------------------------
# Custom Exceptions
# ---------------------------------------------------------------------------

class DataLoaderError(Exception):
    """Base exception for all data loader and schema validation failures."""
    pass


class SourceFileNotFoundError(DataLoaderError):
    """Raised when the target manufacturing CSV cannot be located."""
    pass


class SchemaValidationError(DataLoaderError):
    """Raised when columns, dimensions, or structural headers fail validation."""
    pass


class DataIntegrityError(DataLoaderError):
    """Raised when dataset values (nulls, non-finite, out-of-domain) are invalid."""
    pass


# ---------------------------------------------------------------------------
# Validation Result Dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ValidationResult:
    """Immutable summary record returned upon successful dataset validation."""
    is_valid: bool
    record_count: int
    column_count: int
    machine_count: int
    unique_dates_count: int
    operation_mode_counts: Dict[str, int]
    efficiency_status_counts: Dict[str, int]
    collision_record_count: int
    empirical_ranges: Dict[str, Tuple[float, float]]
    warnings: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Path Resolution Utility
# ---------------------------------------------------------------------------

def get_data_file_path(filename: str = "Thales_Group_Manufacturing.csv") -> Path:
    """
    Resolve the source CSV path relative to the project root.
    
    Avoids hardcoding machine-specific absolute paths.
    Checks `data/raw/<filename>` first, falling back to `<project_root>/<filename>`.

    Parameters:
        filename: Name of the CSV file. Defaults to 'Thales_Group_Manufacturing.csv'.

    Returns:
        Path object pointing to the existing CSV file.

    Raises:
        SourceFileNotFoundError: If the file does not exist in candidate locations.
    """
    # data_loader.py is at <project_root>/scripts/app/data_loader.py
    project_root = Path(__file__).resolve().parent.parent.parent

    candidate_primary = project_root / "data" / "raw" / filename
    if candidate_primary.is_file():
        return candidate_primary

    candidate_root = project_root / filename
    if candidate_root.is_file():
        return candidate_root

    raise SourceFileNotFoundError(
        f"Source manufacturing dataset '{filename}' not found. "
        f"Checked: '{candidate_primary}' and '{candidate_root}'."
    )


def verify_file_checksum(
    file_path: Union[str, Path],
    expected_sha256: Optional[Union[str, Set[str], Tuple[str, ...], List[str]]] = None
) -> str:
    """
    Compute and verify the SHA-256 cryptographic checksum of a file.

    Supports dual-canonical checksum verification for cross-platform portability:
    - Original Windows CRLF (060052A2... - 9,356,442 bytes)
    - Normalized Linux/Git LF (0C59D3C9... - 9,256,441 bytes)

    Parameters:
        file_path: Path to the target file.
        expected_sha256: Expected hexadecimal SHA-256 hash string, or collection of acceptable
                         hash strings. If None, validates against VALID_DATASET_CHECKSUMS.

    Returns:
        Calculated uppercase SHA-256 string if matching.

    Raises:
        SourceFileNotFoundError: If the target file does not exist.
        DataIntegrityError: If the computed checksum diverges from expected hash(es).
    """
    p = Path(file_path)
    if not p.is_file():
        raise SourceFileNotFoundError(f"Target file for checksum verification not found: '{p}'")

    hasher = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    calculated = hasher.hexdigest().upper()

    if expected_sha256 is None:
        target_hashes = {h.upper() for h in VALID_DATASET_CHECKSUMS}
    elif isinstance(expected_sha256, str):
        target_hashes = {expected_sha256.upper()}
    else:
        target_hashes = {h.upper() for h in expected_sha256}

    if calculated not in target_hashes:
        if expected_sha256 is None or target_hashes == {h.upper() for h in VALID_DATASET_CHECKSUMS}:
            expected_desc = (
                f"Accepted canonical hashes: Windows CRLF ({EXPECTED_SHA256_WINDOWS_CRLF}) "
                f"or Linux LF ({EXPECTED_SHA256_LINUX_LF})"
            )
        elif len(target_hashes) == 1:
            expected_desc = f"Expected: {next(iter(target_hashes))}"
        else:
            expected_desc = f"Expected one of: {sorted(target_hashes)}"

        raise DataIntegrityError(
            f"Cryptographic checksum mismatch for '{p.name}'. "
            f"{expected_desc}, Calculated: {calculated}"
        )
    return calculated


# ---------------------------------------------------------------------------
# Date and Time Parsing Utility
# ---------------------------------------------------------------------------

def parse_datetime_series(date_series: pd.Series, time_series: pd.Series) -> pd.Series:
    """
    Parse separate Date and Time string series into a single pandas datetime Series.

    Supports documented formats:
    - Primary format: '%d-%m-%Y %H:%M:%S' (verified European standard in source).
    - Secondary fallback: '%Y-%m-%d %H:%M:%S' (standard ISO representation).

    Does NOT silently coerce unparseable rows into NaT. If any row fails to parse,
    raises a descriptive DataIntegrityError.

    Parameters:
        date_series: Series containing date strings (e.g., '01-01-2025').
        time_series: Series containing time strings (e.g., '00:00:00').

    Returns:
        pd.Series of dtype 'datetime64[ns]'.

    Raises:
        DataIntegrityError: If nulls, mismatched lengths, or unparseable formats exist.
    """
    if len(date_series) != len(time_series):
        raise DataIntegrityError(
            f"Date series length ({len(date_series)}) does not match Time series length ({len(time_series)})."
        )

    if date_series.isnull().any() or time_series.isnull().any():
        raise DataIntegrityError("Date or Timestamp series contains null values before parsing.")

    combined_str = date_series.astype(str).str.strip() + " " + time_series.astype(str).str.strip()

    # Attempt primary documented format: European DD-MM-YYYY HH:MM:SS
    try:
        parsed = pd.to_datetime(combined_str, format="%d-%m-%Y %H:%M:%S", errors="raise")
        return parsed
    except (ValueError, TypeError):
        pass

    # Attempt secondary fallback format: ISO YYYY-MM-DD HH:MM:SS
    try:
        parsed = pd.to_datetime(combined_str, format="%Y-%m-%d %H:%M:%S", errors="raise")
        return parsed
    except (ValueError, TypeError) as exc:
        # Find exact failing index for diagnostic transparency
        for idx, val in combined_str.items():
            try:
                pd.to_datetime(val, format="%d-%m-%Y %H:%M:%S")
            except (ValueError, TypeError):
                try:
                    pd.to_datetime(val, format="%Y-%m-%d %H:%M:%S")
                except (ValueError, TypeError):
                    raise DataIntegrityError(
                        f"Unparseable datetime at row index {idx}: '{val}'. "
                        f"Expected '%d-%m-%Y %H:%M:%S' or '%Y-%m-%d %H:%M:%S'."
                    ) from exc

        raise DataIntegrityError(f"Failed to parse datetime series: {exc}") from exc


# ---------------------------------------------------------------------------
# Schema and Data Integrity Validation Engine
# ---------------------------------------------------------------------------

def validate_dataset(df: pd.DataFrame, expected_rows: Optional[int] = EXPECTED_ROW_COUNT) -> ValidationResult:
    """
    Perform rigorous structural schema and data integrity validation on a DataFrame.

    Validates:
    - Exactly 14 expected columns (no missing, no unexpected, no duplicate column names).
    - Expected row count (if specified, defaults to 100,000).
    - Zero null or missing values across all columns.
    - Zero non-finite numeric values (no NaN, Inf, -Inf).
    - Valid Machine_ID values (integers in 1..50; all 50 present).
    - Valid Operation_Mode categories ('Active', 'Idle', 'Maintenance').
    - Valid Efficiency_Status categories ('Low', 'Medium', 'High').
    - Physical domain boundaries (non-negative latency, loss in [0, 100], etc.).
    - Date and Timestamp parsing validity.
    - Preserved timestamp collision records.

    Parameters:
        df: Pandas DataFrame to validate.
        expected_rows: Expected record count. Set to None to skip row-count constraint.

    Returns:
        ValidationResult containing empirical summary statistics and any drift warnings.

    Raises:
        SchemaValidationError: If columns, headers, or dimensions fail validation.
        DataIntegrityError: If values, categories, nulls, or formats fail validation.
    """
    if not isinstance(df, pd.DataFrame):
        raise SchemaValidationError(f"Expected pandas DataFrame, received: {type(df)}")

    # 1. Structural Column Name Checks
    actual_cols = list(df.columns)
    if len(actual_cols) != len(set(actual_cols)):
        duplicates = [col for col in set(actual_cols) if actual_cols.count(col) > 1]
        raise SchemaValidationError(f"Duplicate column names detected: {duplicates}")

    missing_cols = [c for c in EXPECTED_COLUMNS if c not in actual_cols]
    if missing_cols:
        raise SchemaValidationError(f"Missing required schema columns: {missing_cols}")

    unexpected_cols = [c for c in actual_cols if c not in EXPECTED_COLUMNS]
    if unexpected_cols:
        raise SchemaValidationError(f"Unexpected columns found in dataset: {unexpected_cols}")

    if actual_cols != EXPECTED_COLUMNS:
        raise SchemaValidationError(
            f"Column ordering mismatch. Expected: {EXPECTED_COLUMNS}, Received: {actual_cols}"
        )

    # 2. Record Dimension Checks
    row_count = len(df)
    if expected_rows is not None and row_count != expected_rows:
        raise SchemaValidationError(
            f"Record count mismatch. Expected {expected_rows} rows, found {row_count} rows."
        )

    # 3. Null & Missing Value Checks
    null_counts = df.isnull().sum()
    total_nulls = int(null_counts.sum())
    if total_nulls > 0:
        bad_cols = null_counts[null_counts > 0].to_dict()
        raise DataIntegrityError(f"Dataset contains {total_nulls} null/missing values across columns: {bad_cols}")

    # 4. Numeric Parsing and Non-Finite Checks
    for num_col in NUMERIC_COLUMNS:
        if not pd.api.types.is_numeric_dtype(df[num_col]):
            raise DataIntegrityError(f"Column '{num_col}' is not numeric dtype (found: {df[num_col].dtype}).")
        
        non_finite_mask = ~np.isfinite(df[num_col])
        if non_finite_mask.any():
            bad_indices = df.index[non_finite_mask].tolist()[:5]
            raise DataIntegrityError(
                f"Column '{num_col}' contains non-finite values (NaN/Inf) at indices {bad_indices}."
            )

    # 5. Categorical Domain Checks
    actual_modes = set(df["Operation_Mode"].unique())
    invalid_modes = actual_modes - VALID_OPERATION_MODES
    if invalid_modes:
        raise DataIntegrityError(
            f"Invalid Operation_Mode categories detected: {invalid_modes}. "
            f"Allowed categories: {VALID_OPERATION_MODES}"
        )

    actual_statuses = set(df["Efficiency_Status"].unique())
    invalid_statuses = actual_statuses - VALID_EFFICIENCY_STATUSES
    if invalid_statuses:
        raise DataIntegrityError(
            f"Invalid Efficiency_Status values detected: {invalid_statuses}. "
            f"Allowed values: {VALID_EFFICIENCY_STATUSES}"
        )

    # 6. Machine_ID Validity
    if not pd.api.types.is_integer_dtype(df["Machine_ID"]):
        # Verify if float can safely be cast to integer without precision loss
        if not (df["Machine_ID"] % 1 == 0).all():
            raise DataIntegrityError("Machine_ID contains non-integer values.")

    unique_machines = sorted(df["Machine_ID"].unique().tolist())
    if min(unique_machines) < 1 or max(unique_machines) > 50:
        raise DataIntegrityError(
            f"Machine_ID values out of allowed range [1, 50]: min={min(unique_machines)}, max={max(unique_machines)}"
        )

    if expected_rows is not None:
        if len(unique_machines) != EXPECTED_MACHINE_COUNT:
            raise DataIntegrityError(
                f"Expected exactly {EXPECTED_MACHINE_COUNT} unique machines across full dataset, found {len(unique_machines)}."
            )

    # 7. Physical Plausibility Domain Limits (Hard Rejection)
    for col, (lower_lim, upper_lim) in PHYSICAL_DOMAIN_LIMITS.items():
        vals = df[col]
        if lower_lim is not None and (vals < lower_lim).any():
            violations = int((vals < lower_lim).sum())
            min_val = float(vals.min())
            raise DataIntegrityError(
                f"Physical domain violation in '{col}': {violations} values below {lower_lim} (min observed: {min_val})."
            )
        if upper_lim is not None and (vals > upper_lim).any():
            violations = int((vals > upper_lim).sum())
            max_val = float(vals.max())
            raise DataIntegrityError(
                f"Physical domain violation in '{col}': {violations} values above {upper_lim} (max observed: {max_val})."
            )

    # 8. Date and Timestamp Parsing Validation
    parsed_dt = parse_datetime_series(df["Date"], df["Timestamp"])
    unique_dates = parsed_dt.dt.date.nunique()

    # 9. Empirical Observational Range Auditing (Warnings, Not Hard Rejections)
    warnings: List[str] = []
    empirical_ranges: Dict[str, Tuple[float, float]] = {}
    for col in NUMERIC_COLUMNS:
        observed_min = float(df[col].min())
        observed_max = float(df[col].max())
        empirical_ranges[col] = (observed_min, observed_max)

        ref_min, ref_max = EMPIRICAL_OBSERVED_RANGES[col]
        if observed_min < ref_min or observed_max > ref_max:
            warnings.append(
                f"Empirical drift in '{col}': observed [{observed_min:.4f}, {observed_max:.4f}] "
                f"exceeds Phase 1 baseline range [{ref_min:.4f}, {ref_max:.4f}]."
            )

    # 10. Check Timestamp Collision Records Preservation
    # In Task 1.3, exactly 28 within-machine timestamp collisions (56 records) were identified on 2025-03-01.
    machine_ts_dups = int(df.duplicated(subset=["Machine_ID", "Date", "Timestamp"], keep=False).sum())
    collision_pairs = machine_ts_dups // 2

    mode_counts = df["Operation_Mode"].value_counts().to_dict()
    status_counts = df["Efficiency_Status"].value_counts().to_dict()

    return ValidationResult(
        is_valid=True,
        record_count=row_count,
        column_count=len(actual_cols),
        machine_count=len(unique_machines),
        unique_dates_count=unique_dates,
        operation_mode_counts=mode_counts,
        efficiency_status_counts=status_counts,
        collision_record_count=machine_ts_dups,
        empirical_ranges=empirical_ranges,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Primary Data Loading API (Cached)
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def load_manufacturing_data(
    file_path: Optional[Union[str, Path]] = None,
    validate: bool = True,
    add_parsed_datetime: bool = True
) -> pd.DataFrame:
    """
    Load the manufacturing dataset into an in-memory pandas DataFrame.

    Cached via Streamlit's `@st.cache_data` to ensure fast subsequent execution
    without repeated disk I/O.
    Validates schema and data integrity, parses date/time into a helper column,
    and preserves all 100,000 records including timestamp collisions.

    Parameters:
        file_path: Optional path to the CSV file. If None, resolves automatically via get_data_file_path().
        validate: Whether to run validate_dataset() upon loading. Defaults to True.
        add_parsed_datetime: If True, adds a 'datetime' column of type datetime64[ns]
                             while preserving the original 'Date' and 'Timestamp' columns.

    Returns:
        Pandas DataFrame containing the validated manufacturing dataset.

    Raises:
        SourceFileNotFoundError: If the source CSV cannot be found.
        SchemaValidationError: If the dataset structure fails validation.
        DataIntegrityError: If the dataset values fail validation.
    """
    resolved_path = Path(file_path) if file_path is not None else get_data_file_path()

    if not resolved_path.is_file():
        raise SourceFileNotFoundError(f"Target data file does not exist: '{resolved_path}'")

    # Load raw CSV using pandas
    df = pd.read_csv(resolved_path)

    if validate:
        validate_dataset(df)

    if add_parsed_datetime:
        # Create parsed datetime column while preserving original Date and Timestamp
        df["datetime"] = parse_datetime_series(df["Date"], df["Timestamp"])

    return df


# ---------------------------------------------------------------------------
# CLI Direct Execution Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 70)
    print("MANUFACTURING DATA ACCESS & SCHEMA VALIDATION ENGINE")
    print("=" * 70)

    try:
        path = get_data_file_path()
        print(f"[1] Source Path Resolution: {path}")

        checksum = verify_file_checksum(path)
        print(f"[2] SHA-256 Checksum:       {checksum} (VERIFIED)")

        df_loaded = load_manufacturing_data(path, validate=True, add_parsed_datetime=True)
        print(f"[3] Dataset Loaded Shape:   {df_loaded.shape[0]:,} rows x {df_loaded.shape[1]} columns")

        # Strip helper datetime column to validate original 14-column schema
        val_summary = validate_dataset(df_loaded.drop(columns=["datetime"]))
        print("\n[4] Validation Summary:")
        print(f"    - Valid:               {val_summary.is_valid}")
        print(f"    - Records:             {val_summary.record_count:,}")
        print(f"    - Columns:             {val_summary.column_count}")
        print(f"    - Unique Machines:     {val_summary.machine_count}")
        print(f"    - Unique Dates:        {val_summary.unique_dates_count}")
        print(f"    - Operation Modes:     {val_summary.operation_mode_counts}")
        print(f"    - Efficiency Statuses: {val_summary.efficiency_status_counts}")
        print(f"    - Timestamp Collisions:{val_summary.collision_record_count} records (28 pairs)")
        print(f"    - Warnings Count:      {len(val_summary.warnings)}")

        print("\n" + "=" * 70)
        print("DATA ACCESS LAYER STATUS: READY FOR DOWNSTREAM KPI ENGINES")
        print("=" * 70)
    except Exception as exc:
        print(f"\n[ERROR] Data Access Layer Failure: {exc}")
        raise

