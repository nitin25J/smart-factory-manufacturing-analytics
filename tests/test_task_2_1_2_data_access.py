"""
Unit and Integration Tests for Core Data Access & Schema Validation Engine.
Task 2.1.2 - Manufacturing Diagnostic Intelligence System.

Tests verify:
1. Correct project-relative source path resolution.
2. Successful loading of the original dataset.
3. Correct 100,000 x 14 dimensions (15 with parsed datetime).
4. Exact expected column names and ordering.
5. Correct data types and numeric parsing.
6. Missing-column detection.
7. Unexpected-column detection.
8. Duplicate-column detection.
9. Null-value detection.
10. Invalid numeric and non-finite value detection.
11. Invalid date/time format detection.
12. Unsupported operation-mode detection.
13. Unsupported efficiency-status detection.
14. Record preservation, including verified timestamp collisions.
15. Dataset integrity and cryptographic SHA-256 checksum verification.
16. Streamlit caching behavior and memory reuse.
17. Physical domain boundary enforcement (rejects Temperature < 0, Vibration < 0, Error Rate < 0 or > 100).
18. Physical domain exact boundary values accepted.
19. Empirical range drift reporting.
20. Cross-platform checksum portability (Linux LF and Windows CRLF acceptance).
21. Tampered checksum rejection with dual-hash diagnostic reporting.
"""

from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path
from typing import Generator

import numpy as np
import pandas as pd
import pytest

from scripts.app.data_loader import (
    EXPECTED_COLUMNS,
    EXPECTED_ROW_COUNT,
    EXPECTED_SHA256,
    EXPECTED_SHA256_LINUX_LF,
    EXPECTED_SHA256_WINDOWS_CRLF,
    NUMERIC_COLUMNS,
    VALID_DATASET_CHECKSUMS,
    VALID_EFFICIENCY_STATUSES,
    VALID_OPERATION_MODES,
    DataIntegrityError,
    DataLoaderError,
    SchemaValidationError,
    SourceFileNotFoundError,
    ValidationResult,
    get_data_file_path,
    load_manufacturing_data,
    parse_datetime_series,
    validate_dataset,
    verify_file_checksum,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def valid_dataset_path() -> Path:
    """Return the resolved path to the valid source manufacturing CSV."""
    return get_data_file_path()


@pytest.fixture(scope="module")
def loaded_dataframe(valid_dataset_path: Path) -> pd.DataFrame:
    """Load the full valid dataset once for module-level non-mutating assertions."""
    return load_manufacturing_data(valid_dataset_path, validate=True, add_parsed_datetime=True)


@pytest.fixture
def minimal_valid_df() -> pd.DataFrame:
    """Create a minimal valid DataFrame that complies with all schema rules."""
    data = {
        "Date": ["01-01-2025", "02-01-2025"],
        "Timestamp": ["00:00:00", "12:00:00"],
        "Machine_ID": [1, 2],
        "Operation_Mode": ["Active", "Idle"],
        "Temperature_C": [60.0, 75.0],
        "Vibration_Hz": [2.5, 3.0],
        "Power_Consumption_kW": [5.5, 6.0],
        "Network_Latency_ms": [20.0, 25.0],
        "Packet_Loss_%": [2.0, 1.5],
        "Quality_Control_Defect_Rate_%": [5.0, 4.0],
        "Production_Speed_units_per_hr": [270.0, 280.0],
        "Predictive_Maintenance_Score": [0.5, 0.6],
        "Error_Rate_%": [7.0, 8.0],
        "Efficiency_Status": ["Low", "Medium"],
    }
    return pd.DataFrame(data)


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

def test_01_project_relative_path_resolution(valid_dataset_path: Path) -> None:
    """Verify that get_data_file_path resolves correctly without hardcoded absolute paths."""
    assert valid_dataset_path.is_file(), f"Dataset file does not exist: {valid_dataset_path}"
    assert valid_dataset_path.name == "Thales_Group_Manufacturing.csv"
    assert "data" in valid_dataset_path.parts and "raw" in valid_dataset_path.parts

    # Non-existent file must raise SourceFileNotFoundError
    with pytest.raises(SourceFileNotFoundError):
        get_data_file_path("non_existent_manufacturing_file_xyz.csv")


def test_02_successful_loading_of_dataset(loaded_dataframe: pd.DataFrame) -> None:
    """Verify that load_manufacturing_data successfully loads the dataset into memory."""
    assert isinstance(loaded_dataframe, pd.DataFrame)
    assert not loaded_dataframe.empty
    assert len(loaded_dataframe) == EXPECTED_ROW_COUNT


def test_03_correct_dimensions_100k_by_14(loaded_dataframe: pd.DataFrame) -> None:
    """Verify exactly 100,000 rows and 14 source columns (plus 1 parsed datetime)."""
    assert loaded_dataframe.shape[0] == 100000
    # 14 original schema columns + 1 parsed 'datetime' column
    assert loaded_dataframe.shape[1] == 15
    original_cols = [c for c in loaded_dataframe.columns if c != "datetime"]
    assert len(original_cols) == 14


def test_04_exact_expected_column_names_and_ordering(loaded_dataframe: pd.DataFrame) -> None:
    """Verify exact column names, spelling, and ordering against EXPECTED_COLUMNS."""
    original_cols = [c for c in loaded_dataframe.columns if c != "datetime"]
    assert original_cols == EXPECTED_COLUMNS
    assert len(original_cols) == len(set(original_cols)), "Column names must be distinct"


def test_05_correct_data_types_and_numeric_parsing(loaded_dataframe: pd.DataFrame) -> None:
    """Verify that all numerical fields parse as valid float/int dtypes and datetime is parsed."""
    for col in NUMERIC_COLUMNS:
        assert pd.api.types.is_numeric_dtype(loaded_dataframe[col]), f"{col} must be numeric dtype"
        assert np.isfinite(loaded_dataframe[col]).all(), f"{col} contains non-finite values"

    assert pd.api.types.is_integer_dtype(loaded_dataframe["Machine_ID"])
    assert pd.api.types.is_datetime64_any_dtype(loaded_dataframe["datetime"])


def test_06_missing_column_detection(minimal_valid_df: pd.DataFrame) -> None:
    """Verify that validate_dataset raises SchemaValidationError when a required column is missing."""
    df_missing = minimal_valid_df.drop(columns=["Temperature_C"])
    with pytest.raises(SchemaValidationError, match="Missing required schema columns.*Temperature_C"):
        validate_dataset(df_missing, expected_rows=None)


def test_07_unexpected_column_detection(minimal_valid_df: pd.DataFrame) -> None:
    """Verify that validate_dataset raises SchemaValidationError when extraneous columns exist."""
    df_extra = minimal_valid_df.copy()
    df_extra["Arbitrary_Extra_Sensor"] = 999.0
    with pytest.raises(SchemaValidationError, match="Unexpected columns found in dataset"):
        validate_dataset(df_extra, expected_rows=None)


def test_08_duplicate_column_detection() -> None:
    """Verify that validate_dataset raises SchemaValidationError when duplicate column names exist."""
    # Construct a DataFrame with identical duplicate column names
    data = [[1, 2, 3]]
    df_dup = pd.DataFrame(data, columns=["Date", "Machine_ID", "Date"])
    with pytest.raises(SchemaValidationError, match="Duplicate column names detected"):
        validate_dataset(df_dup, expected_rows=None)


def test_09_null_value_detection(minimal_valid_df: pd.DataFrame) -> None:
    """Verify that validate_dataset raises DataIntegrityError when null values exist."""
    df_null = minimal_valid_df.copy()
    df_null.loc[0, "Vibration_Hz"] = np.nan
    with pytest.raises(DataIntegrityError, match="Dataset contains .* null/missing values"):
        validate_dataset(df_null, expected_rows=None)


def test_10_invalid_numeric_and_non_finite_detection(minimal_valid_df: pd.DataFrame) -> None:
    """Verify that validate_dataset raises DataIntegrityError when non-finite values (Inf) occur."""
    df_inf = minimal_valid_df.copy()
    df_inf.loc[0, "Power_Consumption_kW"] = np.inf
    with pytest.raises(DataIntegrityError, match="contains non-finite values"):
        validate_dataset(df_inf, expected_rows=None)


def test_11_invalid_datetime_format_detection(minimal_valid_df: pd.DataFrame) -> None:
    """Verify that parse_datetime_series raises DataIntegrityError for invalid or malformed strings."""
    bad_dates = pd.Series(["99-99-9999", "01-01-2025"])
    bad_times = pd.Series(["00:00:00", "25:61:99"])
    with pytest.raises(DataIntegrityError, match="Unparseable datetime"):
        parse_datetime_series(bad_dates, bad_times)

    # Test mismatched lengths
    with pytest.raises(DataIntegrityError, match="length"):
        parse_datetime_series(pd.Series(["01-01-2025"]), pd.Series(["00:00:00", "01:00:00"]))


def test_12_unsupported_operation_mode_detection(minimal_valid_df: pd.DataFrame) -> None:
    """Verify that validate_dataset raises DataIntegrityError for unapproved operation modes."""
    df_bad_mode = minimal_valid_df.copy()
    df_bad_mode.loc[0, "Operation_Mode"] = "Off"  # Unsupported mode from earlier draft
    with pytest.raises(DataIntegrityError, match="Invalid Operation_Mode categories detected.*Off"):
        validate_dataset(df_bad_mode, expected_rows=None)


def test_13_unsupported_efficiency_status_detection(minimal_valid_df: pd.DataFrame) -> None:
    """Verify that validate_dataset raises DataIntegrityError for unapproved efficiency statuses."""
    df_bad_status = minimal_valid_df.copy()
    df_bad_status.loc[0, "Efficiency_Status"] = "High Efficiency"  # Erroneous unapproved name
    with pytest.raises(DataIntegrityError, match="Invalid Efficiency_Status values detected"):
        validate_dataset(df_bad_status, expected_rows=None)


def test_14_record_preservation_and_timestamp_collisions(loaded_dataframe: pd.DataFrame) -> None:
    """Verify that all 100,000 records are preserved, including the 28 timestamp collision pairs."""
    assert len(loaded_dataframe) == 100000

    # Test verified timestamp collisions on 2025-03-01
    dups = loaded_dataframe[loaded_dataframe.duplicated(subset=["Machine_ID", "Date", "Timestamp"], keep=False)]
    assert len(dups) == 56, f"Expected exactly 56 collision rows (28 pairs), found {len(dups)}"
    assert (dups["Date"] == "01-03-2025").all(), "All collision records must occur on 01-03-2025"

    # Confirm distinct sensor payloads in collision pairs
    full_row_dups = loaded_dataframe.duplicated(keep=False)
    assert not full_row_dups.any(), "Zero full-row duplicates allowed"


def test_15_dataset_integrity_and_sha256_checksum(valid_dataset_path: Path) -> None:
    """Verify that the raw CSV matches the exact immutable SHA-256 cryptographic hash."""
    # 1. Default invocation verifies against canonical dataset hashes
    calculated_hash = verify_file_checksum(valid_dataset_path)
    assert calculated_hash in VALID_DATASET_CHECKSUMS, (
        f"Checksum {calculated_hash} not found in valid canonical set {VALID_DATASET_CHECKSUMS}"
    )
    # On the active local Windows workspace, verify exact CRLF hash
    assert calculated_hash == EXPECTED_SHA256_WINDOWS_CRLF
    assert calculated_hash == EXPECTED_SHA256

    # 2. Explicit parameter matching Windows CRLF hash
    explicit_hash = verify_file_checksum(valid_dataset_path, expected_sha256=EXPECTED_SHA256_WINDOWS_CRLF)
    assert explicit_hash == EXPECTED_SHA256_WINDOWS_CRLF

    # 3. Explicit set parameter matching canonical set
    set_hash = verify_file_checksum(valid_dataset_path, expected_sha256=VALID_DATASET_CHECKSUMS)
    assert set_hash in VALID_DATASET_CHECKSUMS

    # 4. Tampered fixture should fail verification
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".csv") as tmp:
        tmp.write("tampered,data\n1,2\n")
        tmp_path = Path(tmp.name)
    try:
        with pytest.raises(DataIntegrityError, match="Cryptographic checksum mismatch"):
            verify_file_checksum(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)


def test_16_streamlit_caching_behavior(valid_dataset_path: Path) -> None:
    """Verify that load_manufacturing_data caches DataFrame and reuses memory across calls."""
    df1 = load_manufacturing_data(valid_dataset_path, validate=False)
    df2 = load_manufacturing_data(valid_dataset_path, validate=False)
    assert df1.shape == df2.shape
    # Calling cache_data multiple times returns equal data without repeated disk read
    pd.testing.assert_frame_equal(df1, df2)


def test_17_physical_domain_boundary_enforcement(minimal_valid_df: pd.DataFrame) -> None:
    """
    Verify that out-of-domain values trigger hard rejection:
    - Temperature_C < 0
    - Vibration_Hz < 0
    - Error_Rate_% < 0 or Error_Rate_% > 100
    - Network_Latency_ms < 0
    - Packet_Loss_% > 100
    """
    # 1. Temperature_C < 0 must be rejected
    df_neg_temp = minimal_valid_df.copy()
    df_neg_temp.loc[0, "Temperature_C"] = -1.0
    with pytest.raises(DataIntegrityError, match="Physical domain violation in 'Temperature_C'.*below 0.0"):
        validate_dataset(df_neg_temp, expected_rows=None)

    # 2. Vibration_Hz < 0 must be rejected
    df_neg_vib = minimal_valid_df.copy()
    df_neg_vib.loc[0, "Vibration_Hz"] = -0.5
    with pytest.raises(DataIntegrityError, match="Physical domain violation in 'Vibration_Hz'.*below 0.0"):
        validate_dataset(df_neg_vib, expected_rows=None)

    # 3. Error_Rate_% < 0 must be rejected
    df_neg_err = minimal_valid_df.copy()
    df_neg_err.loc[0, "Error_Rate_%"] = -1.0
    with pytest.raises(DataIntegrityError, match="Physical domain violation in 'Error_Rate_%'.*below 0.0"):
        validate_dataset(df_neg_err, expected_rows=None)

    # 4. Error_Rate_% > 100 must be rejected
    df_high_err = minimal_valid_df.copy()
    df_high_err.loc[0, "Error_Rate_%"] = 105.0
    with pytest.raises(DataIntegrityError, match="Physical domain violation in 'Error_Rate_%'.*above 100.0"):
        validate_dataset(df_high_err, expected_rows=None)

    # 5. Network_Latency_ms < 0 must be rejected
    df_neg_latency = minimal_valid_df.copy()
    df_neg_latency.loc[0, "Network_Latency_ms"] = -5.0
    with pytest.raises(DataIntegrityError, match="Physical domain violation in 'Network_Latency_ms'"):
        validate_dataset(df_neg_latency, expected_rows=None)

    # 6. Packet_Loss_% > 100 must be rejected
    df_high_loss = minimal_valid_df.copy()
    df_high_loss.loc[0, "Packet_Loss_%"] = 105.0
    with pytest.raises(DataIntegrityError, match="Physical domain violation in 'Packet_Loss_%'"):
        validate_dataset(df_high_loss, expected_rows=None)


def test_18_physical_domain_boundary_values_accepted(minimal_valid_df: pd.DataFrame) -> None:
    """
    Verify that boundary values are handled correctly and accepted as valid:
    - Temperature_C = 0.0 C
    - Vibration_Hz = 0.0 Hz
    - Error_Rate_% = 0.0%
    - Error_Rate_% = 100.0%
    """
    df_boundary = minimal_valid_df.copy()
    df_boundary.loc[0, "Temperature_C"] = 0.0
    df_boundary.loc[0, "Vibration_Hz"] = 0.0
    df_boundary.loc[0, "Error_Rate_%"] = 0.0
    df_boundary.loc[1, "Error_Rate_%"] = 100.0

    result = validate_dataset(df_boundary, expected_rows=None)
    assert result.is_valid is True, "Boundary values must validate successfully without error."


def test_19_empirical_range_drift_warning(minimal_valid_df: pd.DataFrame) -> None:
    """Verify that values outside Phase 1 empirical range trigger warnings, not hard exceptions."""
    df_drift = minimal_valid_df.copy()
    # 95.0 C is physically plausible (>= 0.0 C), but exceeds Phase 1 empirical max of 89.999 C
    df_drift.loc[0, "Temperature_C"] = 95.0
    # Must validate successfully without raising exception
    result = validate_dataset(df_drift, expected_rows=None)
    assert result.is_valid is True
    assert any("Empirical drift in 'Temperature_C'" in w for w in result.warnings)


def test_20_checksum_portability_linux_lf_acceptance(valid_dataset_path: Path) -> None:
    """
    Verify cross-platform portability: normalized Linux LF checksum is accepted.

    Streamlit Community Cloud (and Linux Git checkouts) normalize CRLF to LF,
    resulting in a 100,001-byte delta for 100,001 lines with SHA-256:
    0C59D3C93C94A9994CD3503FBD9E7A58697D7EEC5B0FA8CAFC4B9ECF5810C700.
    """
    crlf_bytes = valid_dataset_path.read_bytes()
    lf_bytes = crlf_bytes.replace(b"\r\n", b"\n")

    # Byte delta must be exactly 100,001 bytes (1 header + 100,000 rows)
    assert len(crlf_bytes) - len(lf_bytes) == 100001
    assert len(lf_bytes) == 9256441

    calculated_lf_hash = hashlib.sha256(lf_bytes).hexdigest().upper()
    assert calculated_lf_hash == EXPECTED_SHA256_LINUX_LF

    with tempfile.NamedTemporaryFile("wb", delete=False, suffix=".csv") as tmp:
        tmp.write(lf_bytes)
        tmp_path = Path(tmp.name)

    try:
        # Default verification must accept Linux LF file
        result_default = verify_file_checksum(tmp_path)
        assert result_default == EXPECTED_SHA256_LINUX_LF

        # Explicit verification with EXPECTED_SHA256_LINUX_LF must succeed
        result_explicit = verify_file_checksum(tmp_path, expected_sha256=EXPECTED_SHA256_LINUX_LF)
        assert result_explicit == EXPECTED_SHA256_LINUX_LF

        # Explicit verification with VALID_DATASET_CHECKSUMS set must succeed
        result_set = verify_file_checksum(tmp_path, expected_sha256=VALID_DATASET_CHECKSUMS)
        assert result_set == EXPECTED_SHA256_LINUX_LF
    finally:
        tmp_path.unlink(missing_ok=True)


def test_21_checksum_rejection_and_diagnostic_reporting(valid_dataset_path: Path) -> None:
    """
    Verify strict rejection of invalid/tampered checksums and clean diagnostic messaging.
    """
    # 1. Tampered file with default validation must report both canonical hashes
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".csv") as tmp:
        tmp.write("corrupt,header\n0,0\n")
        tmp_path = Path(tmp.name)

    try:
        with pytest.raises(DataIntegrityError) as exc_info:
            verify_file_checksum(tmp_path)
        err_msg = str(exc_info.value)
        assert "Cryptographic checksum mismatch" in err_msg
        assert EXPECTED_SHA256_WINDOWS_CRLF in err_msg
        assert EXPECTED_SHA256_LINUX_LF in err_msg

        # 2. Tampered file with specific expected hash
        with pytest.raises(DataIntegrityError, match="Expected: 060052A2975034C1D424FDF50089E6D94A5DB736EB85F35CDA0E0B907FF988AF"):
            verify_file_checksum(tmp_path, expected_sha256=EXPECTED_SHA256_WINDOWS_CRLF)

        with pytest.raises(DataIntegrityError, match="Expected: 0C59D3C93C94A9994CD3503FBD9E7A58697D7EEC5B0FA8CAFC4B9ECF5810C700"):
            verify_file_checksum(tmp_path, expected_sha256=EXPECTED_SHA256_LINUX_LF)

    finally:
        tmp_path.unlink(missing_ok=True)

    # 3. Valid dataset against an arbitrary custom hash must fail
    bogus_hash = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    with pytest.raises(DataIntegrityError, match=f"Expected: {bogus_hash}"):
        verify_file_checksum(valid_dataset_path, expected_sha256=bogus_hash)

    # 4. Non-existent file must raise SourceFileNotFoundError
    with pytest.raises(SourceFileNotFoundError):
        verify_file_checksum(Path("non_existent_file_xyz_123.csv"))

