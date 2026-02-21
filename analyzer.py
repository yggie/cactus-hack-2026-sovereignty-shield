"""Analysis pipeline: parse files, chunk messages, run local LLM inference, store findings."""

from __future__ import annotations

import re

from models import (
    CaseFile, Finding, FindingCategory, NormalizedMessage, Severity,
)
from hybrid import generate_hybrid
from db import add_finding, clear_findings, update_case, get_case, get_file_path
from parsers import parse_file

CHUNK_SIZE = 6
CHUNK_OVERLAP = 1


def _chunk_messages(messages: list[NormalizedMessage]) -> list[list[NormalizedMessage]]:
    """Split messages into overlapping windows."""
    if not messages:
        return []
    chunks: list[list[NormalizedMessage]] = []
    step = max(1, CHUNK_SIZE - CHUNK_OVERLAP)
    for i in range(0, len(messages), step):
        chunk = messages[i : i + CHUNK_SIZE]
        if chunk:
            chunks.append(chunk)
    return chunks


def _build_prompt(chunk: list[NormalizedMessage]) -> str:
    """Build an analysis prompt for the LLM from a message chunk."""
    lines = []
    for msg in chunk:
        ts = f"[{msg.timestamp}] " if msg.timestamp else ""
        lines.append(f"{ts}{msg.sender}: {msg.text}")
    conversation = "\n".join(lines)

    return (
        "Analyse this conversation for trafficking and exploitation risk. "
        "Quote the exact concerning text and explain which risk indicator it triggers: "
        "vulnerability, control, isolation, or financial coercion.\n\n"
        f"{conversation}"
    )


# ---------------------------------------------------------------------------
# Text response parsing
# ---------------------------------------------------------------------------

# Keyword patterns for category detection on model output
_CATEGORY_KEYWORDS: list[tuple[FindingCategory, list[re.Pattern[str]]]] = [
    (FindingCategory.THREAT, [
        re.compile(p) for p in [
            r"\bthreat", r"\bviolence", r"\bintimid", r"\bharm\b", r"\bkill\b",
            r"\bhurt\b", r"\battack\b", r"\bdanger\b", r"\bblackmail",
            r"\bcoerce\b", r"\bextort",
        ]
    ]),
    (FindingCategory.SCAM, [
        re.compile(p) for p in [
            r"\bscam", r"\bfraud", r"\bphish", r"\bmoney\b",
            r"\binvestment\b", r"\bwire\b", r"\badvance.fee",
            r"\bdecepti", r"\bponzi", r"\bfinancial\s+(?:harm|loss|exploit)",
        ]
    ]),
    (FindingCategory.ABUSE, [
        re.compile(p) for p in [
            r"\babuse", r"\bcontrol\w*\b", r"\bisolat", r"\bdomestic",
            r"\bcoercive", r"\bmanipulat", r"\bgaslight", r"\bexploit",
            r"\bduress\b", r"\bpower\s+imbalance",
        ]
    ]),
    (FindingCategory.PATTERN, [
        re.compile(p) for p in [
            r"\bpattern", r"\bescalat", r"\brepeat", r"\bcycle",
            r"\bbehavior", r"\bdynamic\b", r"\brecurring",
        ]
    ]),
]

_SEVERITY_HIGH_KEYWORDS = [re.compile(p) for p in [
    r"\bcritical", r"\bsevere\b", r"\bdanger\b", r"\bimminent",
    r"\bkill\b", r"\bhurt\b", r"\bviolence", r"\bextort",
    r"\bblackmail", r"\bimmedi", r"\bcriminal",
]]

_SEVERITY_LOW_KEYWORDS = [re.compile(p) for p in [
    r"\bminor\b", r"\bmild\b", r"\bnormal\b", r"\bno concern",
]]

# Keywords in conversation messages that signal concern (for selecting quotes)
_CONCERNING_MSG_KEYWORDS = [re.compile(p, re.IGNORECASE) for p in [
    r"\bkill\b", r"\bhurt\b", r"\bdebt\b", r"\bowe\b",
    r"\bcan'?t leave", r"\bdelete\b.*\bchat\b", r"\bpassport\b",
    r"\bthreat", r"\bfamily\b", r"\bpolice\b", r"\bphotos?\b",
    r"\bprivate\b", r"\bassociates?\b", r"\bdon'?t tell\b",
    r"\btrust me\b", r"\bonly one\b", r"\bsabotage\b",
    r"\bpay\b.*\bback\b", r"\bcooperate\b", r"\bwire\b",
    r"\binvest\b", r"\bconfidential\b", r"\burgent\b",
    r"\bmoney\b", r"\bsend\b.*\bfund", r"\bcontrol\b",
]]


def _strip_thinking(text: str) -> str:
    """Remove <think>...</think> reasoning traces if present."""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    text = re.sub(r"<think>.*", "", text, flags=re.DOTALL)
    return text.strip()


def _classify_by_keywords(text: str) -> tuple[FindingCategory, Severity]:
    """Classify text by keyword matching."""
    t = text.lower()
    category = FindingCategory.COMMUNICATION
    for cat, patterns in _CATEGORY_KEYWORDS:
        if any(p.search(t) for p in patterns):
            category = cat
            break

    severity = Severity.MEDIUM
    if any(p.search(t) for p in _SEVERITY_HIGH_KEYWORDS):
        severity = Severity.HIGH
    elif any(p.search(t) for p in _SEVERITY_LOW_KEYWORDS):
        severity = Severity.LOW

    return category, severity


def _select_concerning_quote(chunk: list[NormalizedMessage]) -> str:
    """Pick the most concerning message from a chunk by keyword scoring."""
    best_msg = ""
    best_score = -1

    for msg in chunk:
        score = sum(1 for p in _CONCERNING_MSG_KEYWORDS if p.search(msg.text))
        if score > best_score:
            best_score = score
            best_msg = msg.text

    if best_score <= 0:
        for msg in chunk:
            if msg.text.strip():
                return msg.text[:300]

    return best_msg[:300]


def _clean_response(text: str) -> str:
    """Clean model response: strip thinking tags, markdown noise, truncate degeneration."""
    text = _strip_thinking(text)
    if not text:
        return ""

    # Strip markdown headers (### Header, ## Header, etc.)
    text = re.sub(r"^#{1,4}\s+.*$", "", text, flags=re.MULTILINE)
    # Strip emoji characters
    text = re.sub(
        r"[\U0001F300-\U0001F9FF\U00002600-\U000027BF\U0000FE00-\U0000FE0F"
        r"\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF]",
        "", text,
    )
    # Strip markdown bold/italic markers
    text = re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", text)
    # Strip horizontal rules
    text = re.sub(r"^-{3,}$", "", text, flags=re.MULTILINE)
    # Collapse multiple newlines/whitespace
    text = re.sub(r"\n{2,}", " ", text)
    text = re.sub(r"\s{2,}", " ", text)

    # Truncate at repetition (sentence repeated 3+ times = degeneration)
    sentences = re.split(r"(?<=[.!?])\s+", text)
    seen: dict[str, int] = {}
    clean: list[str] = []
    for s in sentences:
        key = s.strip().lower()[:60]
        if not key:
            continue
        seen[key] = seen.get(key, 0) + 1
        if seen[key] >= 3:
            break
        clean.append(s)

    return " ".join(clean).strip()[:500]


def _process_response(
    response_text: str,
    case_id: str,
    file_id: str,
    source: str,
    chunk_index: int,
    chunk: list[NormalizedMessage],
) -> list[Finding]:
    """Convert LLM text response into Finding records."""
    if not response_text or not response_text.strip():
        return []

    explanation = _clean_response(response_text)
    if not explanation or len(explanation) < 20:
        return []

    # Check for explicit "no concerns"
    if re.search(
        r"no\s+concern|nothing\s+wrong|normal\s+conversation|no\s+red\s+flag|no\s+issue",
        explanation.lower(),
    ):
        return []

    # Classify from both model output and conversation text
    cat_model, sev_model = _classify_by_keywords(explanation)

    # Also classify from the conversation itself for better accuracy
    conv_text = " ".join(m.text for m in chunk)
    cat_conv, sev_conv = _classify_by_keywords(conv_text)

    # Prefer the more specific (non-default) classification
    category = cat_model if cat_model != FindingCategory.COMMUNICATION else cat_conv
    # Take the higher severity
    sev_order = [Severity.LOW, Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL]
    severity = max(sev_model, sev_conv, key=lambda s: sev_order.index(s))

    quote = _select_concerning_quote(chunk)

    finding = add_finding(
        case_id=case_id,
        file_id=file_id,
        category=category,
        severity=severity,
        quote=quote,
        explanation=explanation,
        source=source,
        chunk_index=chunk_index,
    )
    return [finding]


# In-memory progress tracking: case_id -> {total, completed, status}
analysis_progress: dict[str, dict] = {}


def analyze_case(case_id: str) -> list[Finding]:
    """Run the full analysis pipeline for a case.

    1. Load all files for the case
    2. Parse each file into normalized messages
    3. Chunk messages (12 per chunk, 2 overlap)
    4. Run local LLM per chunk
    5. Parse text response into findings
    6. Update case status and risk level
    """
    case = get_case(case_id)
    if not case:
        raise ValueError(f"Case {case_id} not found")

    clear_findings(case_id)
    update_case(case_id, status="analyzing")

    all_findings: list[Finding] = []
    total_chunks = 0

    file_chunks: list[tuple[CaseFile, list[list[NormalizedMessage]]]] = []
    for cf in case.files:
        file_path = get_file_path(cf.id)
        if not file_path.exists():
            continue
        text = file_path.read_text(encoding="utf-8", errors="replace")
        _, messages = parse_file(text, cf.filename)
        chunks = _chunk_messages(messages)
        file_chunks.append((cf, chunks))
        total_chunks += len(chunks)

    analysis_progress[case_id] = {"total": total_chunks, "completed": 0, "status": "analyzing"}

    for cf, chunks in file_chunks:
        for i, chunk in enumerate(chunks):
            prompt = _build_prompt(chunk)
            messages = [{"role": "user", "content": prompt}]

            result = generate_hybrid(messages=messages)

            response_text = result.get("response", "")
            findings = _process_response(
                response_text=response_text,
                case_id=case_id,
                file_id=cf.id,
                source=result.get("source", "local"),
                chunk_index=i,
                chunk=chunk,
            )

            all_findings.extend(findings)
            analysis_progress[case_id]["completed"] += 1

    risk = _compute_risk_level(all_findings)
    update_case(case_id, status="complete", risk_level=risk)
    analysis_progress[case_id]["status"] = "complete"

    return all_findings


def _compute_risk_level(findings: list[Finding]) -> str:
    """Compute overall risk level from findings."""
    if not findings:
        return "low"

    severities = [f.severity for f in findings]

    if Severity.CRITICAL in severities:
        return "critical"

    high_count = severities.count(Severity.HIGH)
    if high_count >= 2:
        return "critical"
    if high_count >= 1:
        return "high"

    medium_count = severities.count(Severity.MEDIUM)
    if medium_count >= 3:
        return "high"
    if medium_count >= 1:
        return "medium"

    return "low"


def get_progress(case_id: str) -> dict:
    """Get analysis progress for a case."""
    return analysis_progress.get(case_id, {"total": 0, "completed": 0, "status": "idle"})
