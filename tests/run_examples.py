"""Test scaffold: process each examples/case_* folder through the analysis pipeline.

Each folder is treated as a single case. All files inside are uploaded, analysed,
and a report is generated and saved to examples/output/<folder_name>/report.md.

Uses an isolated SQLite DB + uploads dir under examples/.test_data/ so that the
production data/ directory is never touched.

Usage:
    uv run python tests/run_examples.py            # run all cases
    uv run python tests/run_examples.py case_02     # run a single case
    uv run python tests/run_examples.py --quick     # quick eval: case_01 only, verbose
"""

from __future__ import annotations

import shutil
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Resolve project root so imports work when invoked from any directory
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ---------------------------------------------------------------------------
# Redirect db module to an isolated test directory BEFORE any pipeline import
# triggers init_db() via `from db import ...`
# ---------------------------------------------------------------------------
import db  # noqa: E402 — must import before patching

TEST_DATA_DIR = PROJECT_ROOT / "examples" / ".test_data"
db.DATA_DIR = TEST_DATA_DIR
db.DB_PATH = TEST_DATA_DIR / "test.db"
db.UPLOADS_DIR = TEST_DATA_DIR / "uploads"

EXAMPLES_DIR = PROJECT_ROOT / "examples"
OUTPUT_DIR = EXAMPLES_DIR / "output"

# Binary extensions the text parser can't handle (PDFs are now supported)
_SKIP_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".mp3", ".wav", ".zip"}


def _reset_test_db() -> None:
    """Wipe and re-initialise the test database."""
    if TEST_DATA_DIR.exists():
        shutil.rmtree(TEST_DATA_DIR)
    TEST_DATA_DIR.mkdir(parents=True)
    db.UPLOADS_DIR.mkdir(parents=True)
    db.init_db()


def _discover_cases(filter_name: str | None = None) -> list[Path]:
    """Return sorted list of examples/case_* directories."""
    cases = sorted(
        p for p in EXAMPLES_DIR.iterdir()
        if p.is_dir() and p.name.startswith("case_")
    )
    if filter_name:
        cases = [c for c in cases if c.name == filter_name]
    return cases


def _upload_file(case_id: str, file_path: Path) -> None:
    """Register a file in the DB and copy its content to the uploads dir."""
    from parsers import extract_pdf_text, parse_file

    # For PDFs, extract text first; otherwise read as UTF-8
    if file_path.suffix.lower() == ".pdf":
        text = extract_pdf_text(file_path)
    else:
        text = file_path.read_text(encoding="utf-8", errors="replace")

    fmt, messages = parse_file(text, file_path.name)

    preview = messages[0].text[:80] if messages else ""
    case_file = db.add_file(
        case_id=case_id,
        filename=file_path.name,
        fmt=fmt,
        message_count=len(messages),
        preview=preview,
    )

    # Write extracted text to uploads dir so analyzer can read it
    dest = db.get_file_path(case_file.id)
    dest.write_text(text, encoding="utf-8")


def process_case(case_dir: Path, verbose: bool = False) -> Path:
    """Run the full pipeline for one example case folder.

    Returns the path to the generated report.
    """
    from analyzer import analyze_case
    from report import generate_report

    case_name = case_dir.name
    print(f"\n{'='*60}")
    print(f"  Processing: {case_name}")
    print(f"{'='*60}")

    # 1. Create case
    case = db.create_case(case_name)
    print(f"  Created case {case.id} ({case.name})")

    # 2. Upload every file in the folder
    files = sorted(
        f for f in case_dir.iterdir()
        if f.is_file() and not f.name.startswith(".") and f.suffix.lower() not in _SKIP_EXTS
    )
    for file_path in files:
        _upload_file(case.id, file_path)
        print(f"  Uploaded: {file_path.name}")

    # 3. Analyze
    t0 = time.perf_counter()
    findings = analyze_case(case.id)
    elapsed = time.perf_counter() - t0
    print(f"  Analysis complete: {len(findings)} finding(s) in {elapsed:.2f}s")

    if verbose:
        for f in findings:
            print(f"    [{f.severity.value.upper()}] {f.category.value}: {f.explanation[:100]}")

    # 4. Generate report
    report = generate_report(case.id)
    print(f"  Report generated: risk={report.risk_level.value}, "
          f"findings={report.stats.get('total_findings', 0)}")

    # 5. Save report
    out_dir = OUTPUT_DIR / case_name
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "report.md"
    report_path.write_text(report.markdown, encoding="utf-8")
    print(f"  Saved: {report_path.relative_to(PROJECT_ROOT)}")

    if verbose:
        # Print the report to stdout for quick review
        print(f"\n{'- '*30}")
        print(report.markdown)
        print(f"{'- '*30}")

    return report_path


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    flags = {a for a in sys.argv[1:] if a.startswith("-")}
    filter_name = args[0] if args else None

    quick = "--quick" in flags
    verbose = "--verbose" in flags or "-v" in flags or quick

    # --quick implies case_01 only
    if quick and not filter_name:
        filter_name = "case_01"

    # Verify model loads (will raise RuntimeError if weights missing)
    from inference import MODEL_NAME, _find_weights
    weights = _find_weights()
    if not weights:
        print(f"ERROR: Model weights for {MODEL_NAME} not found.")
        sys.exit(1)

    print(f"Model: {MODEL_NAME} (local-only, on-device)")
    print(f"  Weights: {weights}")

    cases = _discover_cases(filter_name)
    if not cases:
        target = filter_name or "examples/case_*"
        print(f"No example cases found matching: {target}")
        sys.exit(1)

    _reset_test_db()

    print(f"Found {len(cases)} example case(s)")

    reports: list[tuple[str, Path]] = []
    t_start = time.perf_counter()

    for case_dir in cases:
        report_path = process_case(case_dir, verbose=verbose)
        reports.append((case_dir.name, report_path))

    elapsed = time.perf_counter() - t_start

    # Summary
    print(f"\n{'='*60}")
    print(f"  DONE — {len(reports)} case(s) in {elapsed:.2f}s [{MODEL_NAME}]")
    print(f"{'='*60}")
    for name, path in reports:
        print(f"  {name}: {path.relative_to(PROJECT_ROOT)}")
    print()


if __name__ == "__main__":
    main()
