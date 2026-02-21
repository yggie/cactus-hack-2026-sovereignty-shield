"""Compile findings into a STIM-style forensic report with Markdown export.

Report format based on the Sheffield STIM (Sexual Trafficking Identification
Matrix) framework — four Risk Pillars scored 0–10 with evidence citations.
Findings are kept brief in the main body; model elaborations go in the Appendix.
"""

from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from datetime import datetime, timezone

from models import (
    Case, Finding, FindingCategory, Report, RiskLevel, Severity, TimelineEntry,
)
from db import get_case


# ---------------------------------------------------------------------------
# STIM Pillar definitions
# ---------------------------------------------------------------------------

STIM_PILLARS = [
    {
        "name": "Language-Based Vulnerability",
        "short": "Vulnerability",
        "description": "Grooming, flattery, false promises, emotional manipulation",
        "keywords": [
            r"\btrust me\b", r"\bonly one\b", r"\bspecial\b", r"\bpromise\b",
            r"\bopportunit", r"\bflatter", r"\bgroom", r"\blove\b",
            r"\bcare about\b", r"\bchosen\b", r"\bdeserve\b",
            r"\bbeautiful\b", r"\btalent", r"\bpotential\b",
            r"\bmentorship\b", r"\bmentor\b", r"\bprotect\b",
            r"\bstunning\b", r"\bnetwork", r"\bexclusive\b",
            r"\bhigh.value\b", r"\bcareer\b", r"\bmodel",
            r"\bvulnerab", r"\bmanipulat", r"\bexploit",
        ],
        "categories": [FindingCategory.ABUSE, FindingCategory.PATTERN],
    },
    {
        "name": "Third-Party Control",
        "short": "Control",
        "description": "Instructions, demands, restricting movement, authority abuse",
        "keywords": [
            r"\bcontrol\b", r"\bdemand", r"\binstruct", r"\border\b",
            r"\bmust\b", r"\bhave to\b", r"\bpassport\b", r"\btravel\b",
            r"\bpermission\b", r"\brestrict", r"\bcooperat", r"\bobey\b",
            r"\bdo as\b", r"\bfollow\b.*\binstruct", r"\bdon't question\b",
            r"\bconfidential\b", r"\bsecret\b", r"\bencrypted\b",
        ],
        "categories": [FindingCategory.THREAT, FindingCategory.ABUSE],
    },
    {
        "name": "Psychological Isolation",
        "short": "Isolation",
        "description": "Cutting off support networks, enforcing secrecy, gaslighting",
        "keywords": [
            r"\bisolat", r"\bdon'?t tell\b", r"\bdelete\b", r"\bsecre",
            r"\bno one\b.*\bunderstand", r"\bonly I\b", r"\bfamily\b",
            r"\bfriends\b", r"\balone\b", r"\bno contact\b",
            r"\bcut off\b", r"\bgaslight", r"\broommate",
            r"\bdon'?t talk\b", r"\bstay away\b", r"\btrust\b",
        ],
        "categories": [FindingCategory.ABUSE, FindingCategory.PATTERN],
    },
    {
        "name": "Financial Coercion",
        "short": "Financial",
        "description": "Debt traps, withholding pay, financial threats",
        "keywords": [
            r"\bdebt\b", r"\bowe\b", r"\bmoney\b", r"\bpay\b",
            r"\bwire\b", r"\binvest", r"\bfund", r"\bfee\b",
            r"\bfinancial\b", r"\bexpens", r"\bcost\b",
            r"\bpocket\b", r"\btransfer\b", r"\baccount\b",
            r"\bsalary\b", r"\bwithhold", r"\btrap\b",
        ],
        "categories": [FindingCategory.SCAM, FindingCategory.THREAT],
    },
]


# ---------------------------------------------------------------------------
# Pillar scoring
# ---------------------------------------------------------------------------

_SEVERITY_WEIGHT = {
    Severity.LOW: 1,
    Severity.MEDIUM: 2,
    Severity.HIGH: 4,
    Severity.CRITICAL: 6,
}


def _score_pillar(
    pillar: dict,
    findings: list[Finding],
) -> tuple[int, list[Finding]]:
    """Score a STIM pillar 0–10 based on matching findings.

    Returns (score, list of findings that contributed).
    """
    patterns = [re.compile(kw, re.IGNORECASE) for kw in pillar["keywords"]]
    pillar_cats = set(pillar["categories"])

    matched: list[Finding] = []
    raw_score = 0.0

    for f in findings:
        cat_match = f.category in pillar_cats
        text = f"{f.quote} {f.explanation}"
        kw_hits = sum(1 for p in patterns if p.search(text))

        if cat_match or kw_hits > 0:
            matched.append(f)
            weight = _SEVERITY_WEIGHT.get(f.severity, 2)
            raw_score += weight * (1 + kw_hits * 0.3)

    score = min(10, round(raw_score))
    return score, matched


def _signals_for_quote(quote: str) -> list[str]:
    """Identify which STIM pillar signals are present in a quote."""
    signals: list[str] = []
    for pillar in STIM_PILLARS:
        patterns = [re.compile(kw, re.IGNORECASE) for kw in pillar["keywords"]]
        if any(p.search(quote) for p in patterns):
            signals.append(pillar["short"])
    return signals


# ---------------------------------------------------------------------------
# Risk rating
# ---------------------------------------------------------------------------

def _stim_risk_rating(pillar_scores: list[int]) -> tuple[str, int]:
    """Compute STIM probability rating from pillar scores.

    Returns (label, percentage). Total is out of 40 (4 x 10).
    """
    total = sum(pillar_scores)
    pct = min(100, round(total * 100 / 40))

    if pct >= 70:
        label = "CRITICAL RISK"
    elif pct >= 50:
        label = "HIGH RISK"
    elif pct >= 30:
        label = "MEDIUM RISK"
    else:
        label = "LOW RISK"

    return label, pct


def _pillar_rating(score: int) -> str:
    if score >= 7:
        return "CRITICAL"
    if score >= 5:
        return "HIGH"
    if score >= 3:
        return "MEDIUM"
    return "LOW"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_report(case_id: str) -> Report:
    """Generate a STIM-style forensic report from a case's findings."""
    case = get_case(case_id)
    if not case:
        raise ValueError(f"Case {case_id} not found")

    findings = case.findings
    file_map = {f.id: f.filename for f in case.files}

    by_category: dict[str, list[Finding]] = defaultdict(list)
    for f in findings:
        by_category[f.category.value].append(f)

    pillar_results: list[tuple[dict, int, list[Finding]]] = []
    for pillar in STIM_PILLARS:
        score, matched = _score_pillar(pillar, findings)
        pillar_results.append((pillar, score, matched))

    pillar_scores = [score for _, score, _ in pillar_results]
    risk_label, risk_pct = _stim_risk_rating(pillar_scores)

    stats = _compute_stats(findings)
    summary = _generate_summary(case, findings, stats, risk_label, risk_pct)

    report = Report(
        case_id=case_id,
        case_name=case.name,
        generated_at=datetime.now(timezone.utc),
        summary=summary,
        risk_level=case.risk_level,
        timeline=[],
        findings_by_category=by_category,
        stats=stats,
    )
    report.markdown = _render_stim_report(
        report, file_map, findings, pillar_results, risk_label, risk_pct,
    )
    return report


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _compute_stats(findings: list[Finding]) -> dict[str, int | float]:
    total = len(findings)
    local_count = sum(1 for f in findings if f.source == "local")

    severity_counts = {s.value: 0 for s in Severity}
    category_counts = {c.value: 0 for c in FindingCategory}

    for f in findings:
        severity_counts[f.severity.value] += 1
        category_counts[f.category.value] += 1

    return {
        "total_findings": total,
        "local_findings": local_count,
        "local_ratio": round(local_count / total, 2) if total else 1.0,
        **{f"severity_{k}": v for k, v in severity_counts.items()},
        **{f"category_{k}": v for k, v in category_counts.items()},
    }


def _generate_summary(
    case: Case,
    findings: list[Finding],
    stats: dict,
    risk_label: str,
    risk_pct: int,
) -> str:
    total = stats["total_findings"]
    if total == 0:
        return (
            f"Analysis of case \"{case.name}\" found no concerning indicators "
            f"across {len(case.files)} file(s). STIM probability: 0% (LOW RISK)."
        )

    return (
        f"Analysis of {len(case.files)} file(s) in case \"{case.name}\" "
        f"identified {total} indicator(s) of concern. "
        f"STIM probability rating: {risk_pct}% ({risk_label}). "
        f"All analysis performed on-device."
    )


def _category_label(cat: str) -> str:
    labels = {
        "threat": "Threat / Intimidation",
        "scam": "Financial Fraud / Scam",
        "abuse": "Abuse / Control",
        "pattern": "Behavioural Pattern",
        "communication": "Communication Concern",
        "timeline_event": "Timeline Event",
    }
    return labels.get(cat, cat.title())


def _score_bar(score: int) -> str:
    filled = min(score, 10)
    return "\u2588" * filled + "\u2591" * (10 - filled)


def _integrity_hash(report_text: str) -> str:
    """SHA-256 hash of report content for tamper-evidence."""
    return hashlib.sha256(report_text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------

def _render_stim_report(
    report: Report,
    file_map: dict[str, str],
    all_findings: list[Finding],
    pillar_results: list[tuple[dict, int, list[Finding]]],
    risk_label: str,
    risk_pct: int,
) -> str:
    """Render the full STIM forensic report as Markdown."""
    lines: list[str] = []

    # ── Header ──────────────────────────────────────────────
    lines.append("# PRIVATE & CONFIDENTIAL — FORENSIC ANALYSIS REPORT")
    lines.append("")
    lines.append(f"| | |")
    lines.append(f"|---|---|")
    lines.append(f"| **Case Reference** | {report.case_name} |")
    lines.append(f"| **Date of Report** | {report.generated_at.strftime('%B %d, %Y')} |")
    lines.append(f"| **Jurisdiction** | United Kingdom (Common Law) |")
    lines.append(f"| **STIM Rating** | {risk_pct}% ({risk_label}) |")
    lines.append(f"| **Inference** | 100% on-device (local) |")
    lines.append("")

    # ── Section 1: Executive Summary ────────────────────────
    lines.append("## 1. EXECUTIVE SUMMARY")
    lines.append("")
    lines.append(report.summary)
    lines.append("")

    categories_found = [
        cat for cat in ["threat", "scam", "abuse", "pattern"]
        if report.stats.get(f"category_{cat}", 0) > 0
    ]
    if categories_found:
        cat_labels = {
            "threat": "direct threats or intimidation",
            "scam": "financial fraud or scam indicators",
            "abuse": "abusive or controlling behaviour",
            "pattern": "concerning behavioural patterns",
        }
        detected = [cat_labels.get(c, c) for c in categories_found]
        lines.append(f"The analysis detected: {', '.join(detected)}.")
        lines.append("")

    # ── Section 2: STIM Pillar Breakdown ────────────────────
    lines.append("## 2. STIM ANALYSIS (Sheffield STIM Matrix)")
    lines.append("")
    lines.append("| # | Pillar | Score | Rating |")
    lines.append("|---|--------|-------|--------|")
    for i, (pillar, score, _) in enumerate(pillar_results, 1):
        bar = _score_bar(score)
        rating = _pillar_rating(score)
        lines.append(f"| {i} | {pillar['name']} | {bar} {score}/10 | {rating} |")
    lines.append("")

    # Build a lookup: finding id -> list of pillar short names it triggered
    finding_pillars: dict[str, list[str]] = defaultdict(list)
    for pillar, _score, matched in pillar_results:
        for f in matched:
            if pillar["short"] not in finding_pillars[f.id]:
                finding_pillars[f.id].append(pillar["short"])

    # ── Section 3: Key Findings ─────────────────────────────
    lines.append("## 3. KEY FINDINGS")
    lines.append("")

    if not all_findings:
        lines.append("No findings to report.")
        lines.append("")
    else:
        for idx, f in enumerate(all_findings, 1):
            sev = f.severity.value.upper()
            cat_label = _category_label(f.category.value)
            src_file = file_map.get(f.file_id, "unknown")

            # Combine keyword signals from the quote with pillar matches
            pillars_hit = finding_pillars.get(f.id, [])
            if not pillars_hit:
                pillars_hit = _signals_for_quote(f.quote) or ["General"]
            pillars_str = ", ".join(pillars_hit)

            lines.append(f"**Finding {idx}** — {cat_label} | Risk: **{sev}** | "
                         f"Pillars: {pillars_str} | Source: _{src_file}_")
            lines.append(f'> "{f.quote}"')
            lines.append("")

    # ── Section 4: Chain of Custody ─────────────────────────
    lines.append("## 4. CHAIN OF CUSTODY")
    lines.append("")
    file_list = ", ".join(sorted(set(file_map.values())))
    lines.append(f"| | |")
    lines.append(f"|---|---|")
    lines.append(f"| **Source Data** | {len(file_map)} file(s): {file_list} |")
    lines.append(f"| **Processing** | Local on-device inference (no data exfiltration) |")
    lines.append(f"| **Findings** | {report.stats['total_findings']} indicator(s) extracted |")
    lines.append("")

    # ── Section 5: Recommended Actions ──────────────────────
    lines.append("## 5. RECOMMENDED ACTIONS")
    lines.append("")

    actions = _recommend_actions(report, risk_label)
    for j, action in enumerate(actions, 1):
        lines.append(f"{j}. {action}")
    lines.append("")

    # ── Appendix: Detailed Analysis ─────────────────────────
    lines.append("---")
    lines.append("")
    lines.append("## APPENDIX: DETAILED ANALYSIS")
    lines.append("")
    lines.append("*On-device model elaborations for each finding. These are raw "
                 "analytical outputs and may contain imprecise language.*")
    lines.append("")

    for idx, f in enumerate(all_findings, 1):
        cat_label = _category_label(f.category.value)
        lines.append(f"### A{idx}. {cat_label}")
        lines.append("")
        lines.append(f"**Evidence:** \"{f.quote}\"")
        lines.append("")
        lines.append(f"{f.explanation}")
        lines.append("")

    # ── Footer ──────────────────────────────────────────────
    lines.append("---")

    # Compute integrity hash over the body content
    body = "\n".join(lines)
    digest = _integrity_hash(body)
    lines.append(f"**Integrity Hash (SHA-256):** `{digest[:16]}...{digest[-16:]}`")
    lines.append("")
    lines.append(
        "*This report was generated by the Confidential Document Analyst using "
        "the Sheffield STIM Matrix methodology. All analysis was performed "
        "on-device using local inference. This report is intended as a "
        "preliminary analysis aid and should not replace professional legal advice.*"
    )

    return "\n".join(lines)


def _recommend_actions(report: Report, risk_label: str) -> list[str]:
    """Generate recommended actions based on risk level and findings."""
    actions = []

    if "CRITICAL" in risk_label:
        actions.append(
            "**URGENT:** Refer to law enforcement immediately. "
            "Evidence suggests imminent risk of harm or active exploitation."
        )
        actions.append(
            "Preserve all original communications as digital evidence "
            "(do not modify or delete source files)."
        )
    elif "HIGH" in risk_label:
        actions.append(
            "Escalate to a trained safeguarding professional or legal advisor "
            "for further assessment."
        )
        actions.append(
            "Preserve all original communications as potential evidence."
        )

    has_threats = report.stats.get("category_threat", 0) > 0
    has_scam = report.stats.get("category_scam", 0) > 0
    has_abuse = report.stats.get("category_abuse", 0) > 0

    if has_threats:
        actions.append(
            "Document all threats with timestamps and report to police. "
            "Consider emergency safeguarding measures."
        )
    if has_scam:
        actions.append(
            "Report suspected financial fraud to Action Fraud (UK) or "
            "relevant financial crime authority. Advise victim to freeze "
            "any compromised accounts."
        )
    if has_abuse:
        actions.append(
            "Refer to specialist domestic abuse or exploitation support "
            "services (e.g., National Domestic Abuse Helpline, Modern "
            "Slavery Helpline)."
        )

    if not actions:
        actions.append(
            "Continue monitoring. No immediate escalation required based "
            "on current indicators."
        )
        actions.append(
            "Consider periodic re-analysis if new communications are received."
        )

    return actions
