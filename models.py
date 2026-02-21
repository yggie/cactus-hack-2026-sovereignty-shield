"""Pydantic models for the Confidential Document Analyst."""

from __future__ import annotations

import enum
from datetime import datetime

from pydantic import BaseModel, Field


# --- Enums ---

class CaseStatus(str, enum.Enum):
    OPEN = "open"
    ANALYZING = "analyzing"
    COMPLETE = "complete"


class RiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FileFormat(str, enum.Enum):
    WHATSAPP = "whatsapp"
    IMESSAGE = "imessage"
    EMAIL = "email"
    PLAIN_TEXT = "plain_text"
    PDF = "pdf"


class FindingCategory(str, enum.Enum):
    THREAT = "threat"
    SCAM = "scam"
    ABUSE = "abuse"
    PATTERN = "pattern"
    TIMELINE_EVENT = "timeline_event"
    COMMUNICATION = "communication"


class Severity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# --- Core models ---

class CaseFile(BaseModel):
    id: str
    case_id: str
    filename: str
    format: FileFormat
    message_count: int = 0
    preview: str = ""
    created_at: datetime


class Finding(BaseModel):
    id: str
    case_id: str
    file_id: str
    category: FindingCategory
    severity: Severity
    quote: str
    explanation: str
    source: str = "local"  # "local" or "cloud"
    chunk_index: int = 0
    created_at: datetime


class Case(BaseModel):
    id: str
    name: str
    status: CaseStatus = CaseStatus.OPEN
    risk_level: RiskLevel = RiskLevel.LOW
    cloud_consent: bool = False
    created_at: datetime
    files: list[CaseFile] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)


# --- Report models ---

class TimelineEntry(BaseModel):
    date: str
    event: str
    severity: Severity
    source_file: str
    quote: str


class Report(BaseModel):
    case_id: str
    case_name: str
    generated_at: datetime
    summary: str
    risk_level: RiskLevel
    timeline: list[TimelineEntry]
    findings_by_category: dict[str, list[Finding]]
    stats: dict[str, int | float]
    markdown: str = ""


# --- Parser output ---

class NormalizedMessage(BaseModel):
    sender: str
    text: str
    timestamp: str = ""
    source_file: str = ""
    line_number: int = 0
