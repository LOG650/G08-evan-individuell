"""
Fixed reproducibility script for the anonymized LOG650 thesis calculation dataset.

Purpose
-------
This script is intended to replace/clean up Appendix E for reproducibility.
It reads the anonymized mother Excel workbook, recalculates the deterministic
BASSnet indicators, reruns the Monte Carlo model with deterministic input ordering,
and writes auditable output files.

Main fixes compared with the earlier Appendix E logic
-----------------------------------------------------
1. Uses RuntimeError instead of an invalid UnicodeDecodeError constructor.
2. Uses deterministic ordering of Monte Carlo input events.
3. Uses independent random-number streams for Passenger Vessel and Heavy Lift Vessel.
4. Saves input-file hash, deterministic checks, Monte Carlo samples, Monte Carlo summary,
   and a reproducibility audit note.
5. Does not silently claim exact reproduction of old Monte Carlo values if the anonymized
   workbook only contains rounded values or lacks the original Monte Carlo input order.

Requirements
------------
pip install pandas numpy openpyxl

How to run
----------
1. Place this script in the same folder as the anonymized mother workbook.
2. Make sure the workbook is named either:
      Anonymized_Thesis_Calculation_Dataset.xlsx
   or:
      Anonymized_Thesis_Calculation_Dataset(1).xlsx
   You can also edit MOTHER_WORKBOOK below.
3. Run:
      python reproducibility_monte_carlo.py

Output folder
-------------
reproducibility_output/
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import platform
import re
import warnings

import numpy as np
import pandas as pd

# ============================================================
# Reproducibility settings
# ============================================================

RANDOM_SEED = 42
SIM_RUNS = 10_000
OUTPUT_DIR = Path("reproducibility_output")

# Set to True only if you have added a true original Monte Carlo order column
# and full-precision event values, and you expect the old thesis MC table to match exactly.
STRICT_REPORTED_MC_VALIDATION = False

# Leave as None to auto-detect the workbook in the current folder.
MOTHER_WORKBOOK: Path | None = None

WORKBOOK_CANDIDATES = [
    Path("Anonymized_Thesis_Calculation_Dataset.xlsx"),
    Path("Anonymized_Thesis_Calculation_Dataset(1).xlsx"),
]

PASSENGER = "Passenger Vessel, LTSA"
HEAVY = "Heavy Lift Vessel, non-LTSA"

# Deterministic thesis values to validate.
EXPECTED_DETERMINISTIC = {
    "passenger_job_records": 2691,
    "heavy_job_records": 1062,
    "passenger_corrective_jobs": 59,
    "heavy_corrective_jobs": 1,
    "passenger_overdue_jobs": 658,
    "heavy_overdue_jobs": 105,
    "passenger_po_rows": 134,
    "heavy_po_rows": 83,
    "passenger_ordinary_po_count": 50,
    "heavy_ordinary_po_count": 69,
    "passenger_recurring_entries": 66,
    "heavy_recurring_entries": 0,
    "passenger_recurring_exposure": 1_359_948.51,
    "passenger_long_lead_exposure": 58_332.24,
    "passenger_ordinary_exposure": 755_946.97,
    "heavy_ordinary_exposure": 454_868.63,
    "passenger_corrected_exposure": 2_174_227.72,
    "heavy_corrected_exposure": 454_868.63,
    "passenger_spare_records": 104,
    "heavy_spare_records": 121,
    "passenger_stock_above_zero": 16,
    "heavy_stock_above_zero": 112,
    "passenger_total_stock_qty": 30,
    "heavy_total_stock_qty": 777,
    "passenger_stock_value": 7_804.8665,
    "heavy_stock_value": 244_603.7789,
    "heavy_defect_records": 99,
}

# Old reported Monte Carlo table values from the thesis/mother workbook.
# These are kept for comparison only. The corrected script recalculates MC output
# from the event data. Small differences can occur if anonymized event values are rounded
# or if the original MC input order is not included in the anonymized workbook.
REPORTED_MC = {
    "passenger_mean": 2_169_870.79,
    "passenger_median": 2_151_475.36,
    "passenger_std": 207_780.37,
    "passenger_p5": 1_857_507.98,
    "passenger_p95": 2_537_313.49,
    "heavy_mean": 454_327.73,
    "heavy_median": 449_822.85,
    "heavy_std": 92_630.63,
    "heavy_p5": 310_961.59,
    "heavy_p95": 616_492.15,
    "diff_mean": 1_715_543.07,
    "diff_p5": 1_371_638.80,
    "diff_p95": 2_109_030.81,
}


# ============================================================
# Helper functions
# ============================================================

def locate_workbook() -> Path:
    """Find the anonymized mother workbook."""
    if MOTHER_WORKBOOK is not None:
        if not MOTHER_WORKBOOK.exists():
            raise FileNotFoundError(f"Workbook not found: {MOTHER_WORKBOOK}")
        return MOTHER_WORKBOOK

    for candidate in WORKBOOK_CANDIDATES:
        if candidate.exists():
            return candidate

    raise FileNotFoundError(
        "Could not find the anonymized mother workbook. Place it next to this script "
        "or edit MOTHER_WORKBOOK in the script."
    )


def file_hash(path: Path) -> str:
    """Create a SHA-256 hash so the exact input file can be verified."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(8192), b""):
            h.update(block)
    return h.hexdigest()


def read_csv_reproducible(path: Path) -> pd.DataFrame:
    """
    Read CSV files using common encodings for exported operational-system data.

    This fixes the earlier Appendix E issue where UnicodeDecodeError was constructed
    incorrectly. RuntimeError is the correct simple exception here.
    """
    encodings = ["utf-8-sig", "cp1252", "latin1"]
    last_error: Exception | None = None

    for enc in encodings:
        try:
            return pd.read_csv(path, encoding=enc)
        except UnicodeDecodeError as exc:
            last_error = exc
            continue

    raise RuntimeError(
        f"Could not read {path} with utf-8-sig, cp1252, or latin1 encoding."
    ) from last_error


def normalize_text(value: object) -> str:
    """Normalize text for robust comparisons."""
    return str(value).strip().lower()


def normalize_col_name(name: object) -> str:
    """Normalize column names for flexible matching."""
    return (
        str(name)
        .lower()
        .replace(".", "")
        .replace("_", " ")
        .replace("-", " ")
        .strip()
    )


def true_like(series: pd.Series) -> pd.Series:
    """Interpret common yes/no and true/false values."""
    return series.astype(str).str.lower().str.strip().isin(["yes", "y", "true", "1", "x"])


def money_to_float(series: pd.Series) -> pd.Series:
    """Convert monetary values to float while handling commas, blanks, and parentheses."""
    cleaned = (
        series.astype(str)
        .str.replace(",", "", regex=False)
        .str.replace("(", "-", regex=False)
        .str.replace(")", "", regex=False)
        .str.strip()
        .replace(
            {
                "": "0",
                "nan": "0",
                "None": "0",
                "NaN": "0",
                "Not applicable": "0",
                "not applicable": "0",
            }
        )
    )
    return pd.to_numeric(cleaned, errors="coerce").fillna(0.0)


def assert_close(name: str, actual: float, expected: float, tolerance: float = 0.01) -> None:
    """Fail loudly if a calculated value does not match the thesis/mother-doc value."""
    if abs(float(actual) - float(expected)) > tolerance:
        raise AssertionError(
            f"{name} mismatch: actual={actual:.6f}, expected={expected:.6f}, "
            f"difference={actual - expected:.6f}"
        )


def event_id_number(value: object) -> int:
    """Extract the trailing number from IDs such as PV_PO_001 or HL_PO_069."""
    match = re.search(r"(\d+)\s*$", str(value))
    if match:
        return int(match.group(1))
    return 10**9


def read_sheet_table(workbook_path: Path, sheet_name: str) -> pd.DataFrame:
    """Read a normal worksheet with headers in row 1."""
    return pd.read_excel(workbook_path, sheet_name=sheet_name)


def read_summary_sheet(workbook_path: Path, sheet_name: str, header_label: str) -> pd.DataFrame:
    """
    Read a summary worksheet where the actual header row appears below title/blank rows.
    Example header labels: 'Metric', 'Indicator', 'Defect indicator'.
    """
    raw = pd.read_excel(workbook_path, sheet_name=sheet_name, header=None)
    header_row_candidates = raw.index[raw.iloc[:, 0].astype(str).str.strip().eq(header_label)].tolist()
    if not header_row_candidates:
        raise ValueError(f"Could not find header label '{header_label}' in sheet '{sheet_name}'.")

    header_row = header_row_candidates[0]
    headers = raw.iloc[header_row].tolist()
    data = raw.iloc[header_row + 1 :].copy()
    data.columns = headers
    data = data.dropna(how="all")
    return data.reset_index(drop=True)


def metric_value(summary: pd.DataFrame, label_col: str, metric: str, value_col: str) -> object:
    """Get one value from a summary table by row label and column label."""
    rows = summary[summary[label_col].astype(str).str.strip().eq(metric)]
    if rows.empty:
        raise KeyError(f"Metric not found: {metric}")
    return rows.iloc[0][value_col]


# ============================================================
# Deterministic calculations from the mother workbook
# ============================================================

@dataclass(frozen=True)
class POResults:
    passenger_corrected_exposure: float
    heavy_corrected_exposure: float
    passenger_ordinary_values: np.ndarray
    heavy_ordinary_values: np.ndarray
    passenger_recurring_total: float
    heavy_recurring_total: float
    passenger_order_source: str
    heavy_order_source: str
    po_deterministic_summary: pd.DataFrame


def prepare_ordered_events(events: pd.DataFrame, case_label: str) -> tuple[pd.DataFrame, str]:
    """
    Return included events for one case using a deterministic order.

    Best reproducibility practice:
    - If the mother workbook contains MC_Input_Order, Original_Input_Order, or Simulation_Input_Order,
      the script uses that order.
    - If not, it uses Event_ID numerical order. This is deterministic, but it may not reproduce an
      older Monte Carlo table if the original simulation used a different row order or unrounded values.
    """
    required_cols = {"Case", "Event_ID", "Exposure_Category", "Value_USD", "Included_In_Model"}
    missing = required_cols.difference(events.columns)
    if missing:
        raise KeyError(f"PO_Cleaned_Events is missing required columns: {sorted(missing)}")

    included = events[true_like(events["Included_In_Model"])].copy()
    case_events = included[included["Case"].astype(str).str.strip().eq(case_label)].copy()

    order_candidates = ["MC_Input_Order", "Original_Input_Order", "Simulation_Input_Order"]
    order_col = next((col for col in order_candidates if col in case_events.columns), None)

    if order_col is not None:
        case_events["_mc_order"] = pd.to_numeric(case_events[order_col], errors="coerce")
        if case_events["_mc_order"].isna().any():
            raise ValueError(f"{order_col} contains missing/non-numeric values for {case_label}.")
        case_events = case_events.sort_values(["_mc_order", "Event_ID"], kind="mergesort")
        order_source = f"{order_col} column"
    else:
        case_events["_event_id_number"] = case_events["Event_ID"].map(event_id_number)
        case_events = case_events.sort_values(["_event_id_number", "Event_ID"], kind="mergesort")
        order_source = "Event_ID numerical order (fallback; deterministic but may not match old MC order)"

    case_events["_value_usd"] = money_to_float(case_events["Value_USD"])
    return case_events.reset_index(drop=True), order_source


def calculate_po_results(workbook_path: Path) -> POResults:
    """Calculate purchase-order event values from PO_Cleaned_Events."""
    events = read_sheet_table(workbook_path, "PO_Cleaned_Events")

    passenger_events, passenger_order_source = prepare_ordered_events(events, PASSENGER)
    heavy_events, heavy_order_source = prepare_ordered_events(events, HEAVY)

    passenger_ordinary_mask = passenger_events["Exposure_Category"].astype(str).str.contains(
        "ordinary", case=False, na=False
    )
    heavy_ordinary_mask = heavy_events["Exposure_Category"].astype(str).str.contains(
        "ordinary", case=False, na=False
    )

    passenger_ordinary = passenger_events.loc[passenger_ordinary_mask].copy()
    passenger_recurring = passenger_events.loc[~passenger_ordinary_mask].copy()
    heavy_ordinary = heavy_events.loc[heavy_ordinary_mask].copy()
    heavy_recurring = heavy_events.loc[~heavy_ordinary_mask].copy()

    passenger_corrected = float(passenger_events["_value_usd"].sum())
    heavy_corrected = float(heavy_events["_value_usd"].sum())

    passenger_ordinary_values = passenger_ordinary["_value_usd"].to_numpy(dtype=float)
    heavy_ordinary_values = heavy_ordinary["_value_usd"].to_numpy(dtype=float)
    passenger_recurring_total = float(passenger_recurring["_value_usd"].sum())
    heavy_recurring_total = float(heavy_recurring["_value_usd"].sum())

    # Build deterministic PO summary directly from event table.
    rows = []
    for case_label, case_events, ordinary_events, recurring_events in [
        (PASSENGER, passenger_events, passenger_ordinary, passenger_recurring),
        (HEAVY, heavy_events, heavy_ordinary, heavy_recurring),
    ]:
        values = case_events["_value_usd"]
        total = float(values.sum())
        rows.append(
            {
                "case": case_label,
                "included_po_events": int(len(case_events)),
                "ordinary_latest_non_cancelled_po_events": int(len(ordinary_events)),
                "recurring_and_long_lead_events": int(len(recurring_events)),
                "ordinary_exposure_usd": float(ordinary_events["_value_usd"].sum()),
                "recurring_and_long_lead_exposure_usd": float(recurring_events["_value_usd"].sum()),
                "corrected_po_exposure_usd": total,
                "mean_corrected_event_value_usd": float(values.mean()),
                "std_corrected_event_value_usd": float(values.std(ddof=1)),
                "coefficient_of_variation": float(values.std(ddof=1) / values.mean()),
                "top_five_concentration": float(values.nlargest(5).sum() / total),
            }
        )

    return POResults(
        passenger_corrected_exposure=passenger_corrected,
        heavy_corrected_exposure=heavy_corrected,
        passenger_ordinary_values=passenger_ordinary_values,
        heavy_ordinary_values=heavy_ordinary_values,
        passenger_recurring_total=passenger_recurring_total,
        heavy_recurring_total=heavy_recurring_total,
        passenger_order_source=passenger_order_source,
        heavy_order_source=heavy_order_source,
        po_deterministic_summary=pd.DataFrame(rows),
    )


def validate_deterministic_tables(workbook_path: Path, po_results: POResults) -> pd.DataFrame:
    """Validate deterministic workbook values against the thesis values."""
    job_summary = read_summary_sheet(workbook_path, "Job_History", "Metric")
    spares_summary = read_summary_sheet(workbook_path, "SpareParts_Summary", "Indicator")
    defects_summary = read_summary_sheet(workbook_path, "Defects_Summary", "Defect indicator")
    po_summary = read_summary_sheet(workbook_path, "PO_Summary", "Indicator")

    rows = []

    def add_check(name: str, actual: float, expected: float, tolerance: float = 0.01) -> None:
        difference = float(actual) - float(expected)
        status = "OK" if abs(difference) <= tolerance else "CHECK"
        rows.append(
            {
                "check": name,
                "actual": float(actual),
                "expected": float(expected),
                "difference": difference,
                "tolerance": tolerance,
                "status": status,
            }
        )
        assert_close(name, float(actual), float(expected), tolerance=tolerance)

    # Job-history checks.
    add_check(
        "Passenger job-history records",
        metric_value(job_summary, "Metric", "Job-history records", PASSENGER),
        EXPECTED_DETERMINISTIC["passenger_job_records"],
    )
    add_check(
        "Heavy Lift job-history records",
        metric_value(job_summary, "Metric", "Job-history records", HEAVY),
        EXPECTED_DETERMINISTIC["heavy_job_records"],
    )
    add_check(
        "Passenger corrective job records",
        metric_value(job_summary, "Metric", "Corrective job records, based on Job Class", PASSENGER),
        EXPECTED_DETERMINISTIC["passenger_corrective_jobs"],
    )
    add_check(
        "Heavy Lift corrective job records",
        metric_value(job_summary, "Metric", "Corrective job records, based on Job Class", HEAVY),
        EXPECTED_DETERMINISTIC["heavy_corrective_jobs"],
    )
    add_check(
        "Passenger overdue job records",
        metric_value(job_summary, "Metric", "Overdue job records", PASSENGER),
        EXPECTED_DETERMINISTIC["passenger_overdue_jobs"],
    )
    add_check(
        "Heavy Lift overdue job records",
        metric_value(job_summary, "Metric", "Overdue job records", HEAVY),
        EXPECTED_DETERMINISTIC["heavy_overdue_jobs"],
    )

    # Purchase-order checks from summary sheet and from recalculated event table.
    add_check(
        "Passenger purchase-order rows",
        metric_value(po_summary, "Indicator", "Purchase-order rows", PASSENGER),
        EXPECTED_DETERMINISTIC["passenger_po_rows"],
    )
    add_check(
        "Heavy Lift purchase-order rows",
        metric_value(po_summary, "Indicator", "Purchase-order rows", HEAVY),
        EXPECTED_DETERMINISTIC["heavy_po_rows"],
    )
    add_check(
        "Passenger ordinary latest-version non-cancelled POs",
        metric_value(po_summary, "Indicator", "Ordinary latest-version non-cancelled POs", PASSENGER),
        EXPECTED_DETERMINISTIC["passenger_ordinary_po_count"],
    )
    add_check(
        "Heavy Lift ordinary latest-version non-cancelled POs",
        metric_value(po_summary, "Indicator", "Ordinary latest-version non-cancelled POs", HEAVY),
        EXPECTED_DETERMINISTIC["heavy_ordinary_po_count"],
    )
    add_check(
        "Passenger corrected PO exposure from event table",
        po_results.passenger_corrected_exposure,
        EXPECTED_DETERMINISTIC["passenger_corrected_exposure"],
    )
    add_check(
        "Heavy Lift corrected PO exposure from event table",
        po_results.heavy_corrected_exposure,
        EXPECTED_DETERMINISTIC["heavy_corrected_exposure"],
    )
    add_check(
        "Passenger recurring + long-lead exposure from event table",
        po_results.passenger_recurring_total,
        EXPECTED_DETERMINISTIC["passenger_recurring_exposure"] + EXPECTED_DETERMINISTIC["passenger_long_lead_exposure"],
    )
    add_check(
        "Passenger ordinary PO exposure from event table",
        po_results.passenger_ordinary_values.sum(),
        EXPECTED_DETERMINISTIC["passenger_ordinary_exposure"],
    )
    add_check(
        "Heavy Lift ordinary PO exposure from event table",
        po_results.heavy_ordinary_values.sum(),
        EXPECTED_DETERMINISTIC["heavy_ordinary_exposure"],
    )

    # Spare-parts checks.
    add_check(
        "Passenger spare-parts records",
        metric_value(spares_summary, "Indicator", "Spare-parts records", PASSENGER),
        EXPECTED_DETERMINISTIC["passenger_spare_records"],
    )
    add_check(
        "Heavy Lift spare-parts records",
        metric_value(spares_summary, "Indicator", "Spare-parts records", HEAVY),
        EXPECTED_DETERMINISTIC["heavy_spare_records"],
    )
    add_check(
        "Passenger spare-parts records with stock above zero",
        metric_value(spares_summary, "Indicator", "Spare-parts records with stock above zero", PASSENGER),
        EXPECTED_DETERMINISTIC["passenger_stock_above_zero"],
    )
    add_check(
        "Heavy Lift spare-parts records with stock above zero",
        metric_value(spares_summary, "Indicator", "Spare-parts records with stock above zero", HEAVY),
        EXPECTED_DETERMINISTIC["heavy_stock_above_zero"],
    )
    add_check(
        "Passenger spare-parts stock-value indicator",
        metric_value(spares_summary, "Indicator", "Spare-parts stock-value indicator, USD", PASSENGER),
        EXPECTED_DETERMINISTIC["passenger_stock_value"],
    )
    add_check(
        "Heavy Lift spare-parts stock-value indicator",
        metric_value(spares_summary, "Indicator", "Spare-parts stock-value indicator, USD", HEAVY),
        EXPECTED_DETERMINISTIC["heavy_stock_value"],
    )

    # Defect checks.
    add_check(
        "Heavy Lift defect records",
        metric_value(defects_summary, "Defect indicator", "Total defect records", HEAVY),
        EXPECTED_DETERMINISTIC["heavy_defect_records"],
    )

    return pd.DataFrame(rows)


# ============================================================
# Monte Carlo simulation
# ============================================================

def simulate_procurement_exposure(
    recurring_total: float,
    ordinary_values: np.ndarray,
    rng: np.random.Generator,
    runs: int = SIM_RUNS,
) -> np.ndarray:
    """
    Simulate procurement exposure.

    Recurring agreement exposure is retained as observed.
    Ordinary purchase-order exposure is simulated with:
    - Poisson event count, lambda = observed ordinary event count
    - sampling with replacement from observed ordinary purchase-order values
    """
    ordinary_values = np.asarray(ordinary_values, dtype=float)
    if ordinary_values.ndim != 1 or len(ordinary_values) == 0:
        raise ValueError("ordinary_values must be a non-empty one-dimensional array.")

    lam = len(ordinary_values)
    n_events = rng.poisson(lam=lam, size=runs)
    simulated_totals = np.empty(runs, dtype=float)

    for i, n in enumerate(n_events):
        if n > 0:
            simulated_totals[i] = recurring_total + rng.choice(
                ordinary_values,
                size=int(n),
                replace=True,
            ).sum()
        else:
            simulated_totals[i] = recurring_total

    return simulated_totals


def summarize_simulation(values: np.ndarray) -> dict[str, float]:
    """Return standard Monte Carlo summary statistics."""
    return {
        "mean": float(values.mean()),
        "median": float(np.median(values)),
        "standard_deviation": float(values.std(ddof=1)),
        "p5": float(np.percentile(values, 5)),
        "p95": float(np.percentile(values, 95)),
    }


def run_monte_carlo(po_results: POResults) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Run Monte Carlo simulation using independent RNG streams.

    Independent streams make the Passenger Vessel result independent of whether the Heavy Lift
    simulation is run before/after it. This improves reproducibility and auditability.
    """
    seed_sequence = np.random.SeedSequence(RANDOM_SEED)
    passenger_seed, heavy_seed = seed_sequence.spawn(2)
    passenger_rng = np.random.default_rng(passenger_seed)
    heavy_rng = np.random.default_rng(heavy_seed)

    passenger_values = simulate_procurement_exposure(
        recurring_total=po_results.passenger_recurring_total,
        ordinary_values=po_results.passenger_ordinary_values,
        rng=passenger_rng,
        runs=SIM_RUNS,
    )
    heavy_values = simulate_procurement_exposure(
        recurring_total=po_results.heavy_recurring_total,
        ordinary_values=po_results.heavy_ordinary_values,
        rng=heavy_rng,
        runs=SIM_RUNS,
    )
    difference_values = passenger_values - heavy_values

    passenger_summary = summarize_simulation(passenger_values)
    heavy_summary = summarize_simulation(heavy_values)
    difference_summary = summarize_simulation(difference_values)

    mc_summary = pd.DataFrame(
        [
            {"case": PASSENGER, **passenger_summary},
            {"case": HEAVY, **heavy_summary},
            {"case": "Difference, Passenger minus Heavy Lift", **difference_summary},
        ]
    )

    probability_summary = pd.DataFrame(
        [
            {
                "probability_passenger_exposure_higher": float((passenger_values > heavy_values).mean()),
                "probability_heavy_lift_exposure_higher": float((heavy_values > passenger_values).mean()),
            }
        ]
    )

    samples = pd.DataFrame(
        {
            "run_id": np.arange(1, SIM_RUNS + 1),
            "passenger_exposure_usd": passenger_values,
            "heavy_lift_exposure_usd": heavy_values,
            "difference_passenger_minus_heavy_usd": difference_values,
        }
    )

    return mc_summary, probability_summary, samples


def compare_with_reported_mc(mc_summary: pd.DataFrame) -> pd.DataFrame:
    """Compare recalculated MC values with the older reported thesis MC values."""
    passenger = mc_summary.loc[mc_summary["case"].eq(PASSENGER)].iloc[0]
    heavy = mc_summary.loc[mc_summary["case"].eq(HEAVY)].iloc[0]
    diff = mc_summary.loc[mc_summary["case"].str.startswith("Difference")].iloc[0]

    comparisons = [
        ("Passenger mean", passenger["mean"], REPORTED_MC["passenger_mean"]),
        ("Passenger median", passenger["median"], REPORTED_MC["passenger_median"]),
        ("Passenger standard deviation", passenger["standard_deviation"], REPORTED_MC["passenger_std"]),
        ("Passenger p5", passenger["p5"], REPORTED_MC["passenger_p5"]),
        ("Passenger p95", passenger["p95"], REPORTED_MC["passenger_p95"]),
        ("Heavy Lift mean", heavy["mean"], REPORTED_MC["heavy_mean"]),
        ("Heavy Lift median", heavy["median"], REPORTED_MC["heavy_median"]),
        ("Heavy Lift standard deviation", heavy["standard_deviation"], REPORTED_MC["heavy_std"]),
        ("Heavy Lift p5", heavy["p5"], REPORTED_MC["heavy_p5"]),
        ("Heavy Lift p95", heavy["p95"], REPORTED_MC["heavy_p95"]),
        ("Difference mean", diff["mean"], REPORTED_MC["diff_mean"]),
        ("Difference p5", diff["p5"], REPORTED_MC["diff_p5"]),
        ("Difference p95", diff["p95"], REPORTED_MC["diff_p95"]),
    ]

    rows = []
    for metric, recalculated, reported in comparisons:
        difference = float(recalculated) - float(reported)
        rows.append(
            {
                "metric": metric,
                "recalculated_from_mother_doc": float(recalculated),
                "reported_old_thesis_value": float(reported),
                "difference": difference,
                "absolute_difference": abs(difference),
            }
        )

    comparison_df = pd.DataFrame(rows)

    if STRICT_REPORTED_MC_VALIDATION:
        for _, row in comparison_df.iterrows():
            assert_close(
                row["metric"],
                row["recalculated_from_mother_doc"],
                row["reported_old_thesis_value"],
                tolerance=0.01,
            )

    return comparison_df


# ============================================================
# Sensitivity calculations
# ============================================================

def calculate_sensitivity(po_results: POResults, workbook_path: Path) -> pd.DataFrame:
    """Calculate break-even and sensitivity checks."""
    spares_summary = read_summary_sheet(workbook_path, "SpareParts_Summary", "Indicator")
    passenger_stock_value = float(
        metric_value(spares_summary, "Indicator", "Spare-parts stock-value indicator, USD", PASSENGER)
    )
    heavy_stock_value = float(
        metric_value(spares_summary, "Indicator", "Spare-parts stock-value indicator, USD", HEAVY)
    )

    passenger_po = po_results.passenger_corrected_exposure
    heavy_po = po_results.heavy_corrected_exposure

    heavy_break_even_factor = passenger_po / heavy_po
    passenger_reduction_factor = heavy_po / passenger_po
    spare_parts_weight_factor = (passenger_po - heavy_po) / (heavy_stock_value - passenger_stock_value)

    return pd.DataFrame(
        [
            {
                "sensitivity_test": "Heavy Lift Vessel purchase-order break-even factor",
                "result": heavy_break_even_factor,
                "rounded_thesis_result": round(heavy_break_even_factor, 2),
                "interpretation": "Heavy Lift exposure factor needed to equal Passenger corrected PO exposure.",
            },
            {
                "sensitivity_test": "Passenger Vessel purchase-order reduction factor",
                "result": passenger_reduction_factor,
                "rounded_thesis_result": round(passenger_reduction_factor, 2),
                "interpretation": "Passenger exposure share needed to equal Heavy Lift corrected PO exposure.",
            },
            {
                "sensitivity_test": "Spare-parts stock-value break-even factor",
                "result": spare_parts_weight_factor,
                "rounded_thesis_result": round(spare_parts_weight_factor, 2),
                "interpretation": "Spare-parts stock exposure weight needed before overturning PO exposure difference.",
            },
            {
                "sensitivity_test": "Recorded downtime sensitivity",
                "result": np.nan,
                "rounded_thesis_result": np.nan,
                "interpretation": "Inconclusive because both cases have zero positive recorded downtime hours.",
            },
        ]
    )


# ============================================================
# Main workflow
# ============================================================

def write_audit_note(
    workbook_path: Path,
    po_results: POResults,
    mc_comparison: pd.DataFrame,
) -> None:
    """Write a plain-text audit note explaining exact reproducibility status."""
    OUTPUT_DIR.mkdir(exist_ok=True)

    max_abs_mc_difference = float(mc_comparison["absolute_difference"].max())

    note = f"""Reproducibility audit note
==========================

Input workbook: {workbook_path}
Input workbook SHA-256: {file_hash(workbook_path)}
Python version: {platform.python_version()}
pandas version: {pd.__version__}
NumPy version: {np.__version__}
Random seed: {RANDOM_SEED}
Simulation runs: {SIM_RUNS}

Monte Carlo input order
-----------------------
Passenger Vessel order source: {po_results.passenger_order_source}
Heavy Lift Vessel order source: {po_results.heavy_order_source}

Important note
--------------
The deterministic workbook calculations are validated against the thesis values.
The Monte Carlo simulation is now reproducible because it uses deterministic event ordering
and independent random-number streams.

If the recalculated Monte Carlo table differs from an older thesis table, that does not mean
the deterministic calculations are wrong. It means the old Monte Carlo output was generated
from a specific input order and/or full-precision values that may not be fully preserved in the
anonymized mother workbook. To reproduce the old Monte Carlo output exactly, add an
MC_Input_Order column and use full-precision Value_USD values from the original model input.

Maximum absolute difference versus older reported MC table: {max_abs_mc_difference:.6f} USD
"""

    (OUTPUT_DIR / "reproducibility_audit_note.txt").write_text(note, encoding="utf-8")


def main() -> None:
    workbook_path = locate_workbook()
    OUTPUT_DIR.mkdir(exist_ok=True)

    print("Environment")
    print("-----------")
    print(f"Python version: {platform.python_version()}")
    print(f"pandas version: {pd.__version__}")
    print(f"NumPy version: {np.__version__}")
    print(f"Random seed: {RANDOM_SEED}")
    print(f"Simulation runs: {SIM_RUNS}")
    print()

    print("Input-file integrity")
    print("--------------------")
    print(f"Workbook: {workbook_path}")
    print(f"SHA-256: {file_hash(workbook_path)}")
    print()

    po_results = calculate_po_results(workbook_path)
    deterministic_checks = validate_deterministic_tables(workbook_path, po_results)
    sensitivity = calculate_sensitivity(po_results, workbook_path)
    mc_summary, probability_summary, mc_samples = run_monte_carlo(po_results)
    mc_comparison = compare_with_reported_mc(mc_summary)

    # Export outputs.
    deterministic_checks.to_csv(OUTPUT_DIR / "deterministic_validation_checks.csv", index=False)
    po_results.po_deterministic_summary.to_csv(OUTPUT_DIR / "po_deterministic_summary.csv", index=False)
    sensitivity.to_csv(OUTPUT_DIR / "sensitivity_checks.csv", index=False)
    mc_summary.to_csv(OUTPUT_DIR / "monte_carlo_summary_recalculated.csv", index=False)
    probability_summary.to_csv(OUTPUT_DIR / "monte_carlo_probability_summary.csv", index=False)
    mc_comparison.to_csv(OUTPUT_DIR / "monte_carlo_comparison_vs_old_reported.csv", index=False)
    mc_samples.to_csv(OUTPUT_DIR / "monte_carlo_samples_recalculated.csv", index=False)
    write_audit_note(workbook_path, po_results, mc_comparison)

    # Console output.
    print("All deterministic validation checks passed.")
    print()
    print("PO deterministic summary")
    print("------------------------")
    print(po_results.po_deterministic_summary.to_string(index=False))
    print()
    print("Sensitivity checks")
    print("------------------")
    print(sensitivity.to_string(index=False))
    print()
    print("Monte Carlo summary, recalculated")
    print("---------------------------------")
    print(mc_summary.to_string(index=False))
    print()
    print("Monte Carlo probability summary")
    print("-------------------------------")
    print(probability_summary.to_string(index=False))
    print()

    max_abs_diff = float(mc_comparison["absolute_difference"].max())
    if max_abs_diff > 0.01:
        warnings.warn(
            "The recalculated Monte Carlo output differs from the older reported MC table. "
            "This is expected if the anonymized workbook lacks original MC_Input_Order or full-precision values. "
            "See reproducibility_output/reproducibility_audit_note.txt.",
            RuntimeWarning,
        )
        print("Monte Carlo comparison versus old reported table")
        print("------------------------------------------------")
        print(mc_comparison.to_string(index=False))
        print()

    print(f"Output files saved to: {OUTPUT_DIR.resolve()}")


if __name__ == "__main__":
    main()
