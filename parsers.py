"""File format detection and parsing into NormalizedMessage sequences."""

from __future__ import annotations

import re
from pathlib import Path

from models import FileFormat, NormalizedMessage


# --- Format detection ---

# WhatsApp: "1/15/24, 2:30 PM - Sender: message" or "[1/15/24, 14:30:00] Sender: message"
_WA_PATTERN = re.compile(
    r"^[\[\d]?\d{1,2}/\d{1,2}/\d{2,4},?\s+\d{1,2}[:.]\d{2}"
)

# iMessage export (common formats): "From: Name" / "Date:" blocks, or CSV-like
_IMESSAGE_PATTERN = re.compile(
    r"^(From|To|Date|Subject):\s", re.MULTILINE
)

# Email (.eml style): headers like From:, To:, Subject:, MIME
_EMAIL_PATTERN = re.compile(
    r"^(From|To|Subject|MIME-Version|Content-Type):\s", re.MULTILINE
)


def detect_format(text: str, filename: str = "") -> FileFormat:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext == "pdf":
        return FileFormat.PDF

    if ext == "eml":
        return FileFormat.EMAIL

    # Check content patterns
    lines = text[:2000]  # Only scan first 2KB

    if _WA_PATTERN.search(lines):
        return FileFormat.WHATSAPP

    email_hits = len(_EMAIL_PATTERN.findall(lines))
    if email_hits >= 3 or ext == "eml":
        return FileFormat.EMAIL

    imessage_hits = len(_IMESSAGE_PATTERN.findall(lines))
    if imessage_hits >= 2 and ext != "eml":
        return FileFormat.IMESSAGE

    return FileFormat.PLAIN_TEXT


# --- Parsers ---

# WhatsApp line: "1/15/24, 2:30 PM - Sender: message text here"
_WA_MSG = re.compile(
    r"^(\d{1,2}/\d{1,2}/\d{2,4},?\s+\d{1,2}[:.]\d{2}(?:[:.]\d{2})?\s*(?:AM|PM|am|pm)?)\s*[-–]\s*(.+?):\s(.+)"
)

# Bracketed variant: "[15/01/2024, 14:30:00] Sender: message"
_WA_MSG_BRACKET = re.compile(
    r"^\[(\d{1,2}/\d{1,2}/\d{2,4},?\s+\d{1,2}[:.]\d{2}(?:[:.]\d{2})?)\]\s*(.+?):\s(.+)"
)


def parse_whatsapp(text: str, source_file: str = "") -> list[NormalizedMessage]:
    messages: list[NormalizedMessage] = []
    for i, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        m = _WA_MSG.match(line) or _WA_MSG_BRACKET.match(line)
        if m:
            messages.append(NormalizedMessage(
                sender=m.group(2).strip(),
                text=m.group(3).strip(),
                timestamp=m.group(1).strip(),
                source_file=source_file,
                line_number=i,
            ))
        elif messages:
            # Continuation of previous message
            messages[-1].text += " " + line
    return messages


def parse_email(text: str, source_file: str = "") -> list[NormalizedMessage]:
    messages: list[NormalizedMessage] = []
    # Split on common email separators
    parts = re.split(r"\n(?=From:\s)", text)

    for part in parts:
        from_match = re.search(r"^From:\s*(.+)$", part, re.MULTILINE)
        date_match = re.search(r"^Date:\s*(.+)$", part, re.MULTILINE)
        # Body is everything after the first blank line following headers
        header_end = re.search(r"\n\s*\n", part)
        body = part[header_end.end():].strip() if header_end else part.strip()

        if body:
            messages.append(NormalizedMessage(
                sender=from_match.group(1).strip() if from_match else "Unknown",
                text=body[:500],  # Cap email body length
                timestamp=date_match.group(1).strip() if date_match else "",
                source_file=source_file,
            ))

    return messages


def parse_imessage(text: str, source_file: str = "") -> list[NormalizedMessage]:
    # Generic structured message format with From:/Date: headers
    messages: list[NormalizedMessage] = []
    parts = re.split(r"\n(?=From:\s)", text)

    for part in parts:
        from_match = re.search(r"^From:\s*(.+)$", part, re.MULTILINE)
        date_match = re.search(r"^Date:\s*(.+)$", part, re.MULTILINE)
        # Message body: lines that aren't headers
        body_lines = [
            l for l in part.splitlines()
            if not re.match(r"^(From|To|Date|Subject):\s", l)
        ]
        body = " ".join(l.strip() for l in body_lines if l.strip())

        if body:
            messages.append(NormalizedMessage(
                sender=from_match.group(1).strip() if from_match else "Unknown",
                text=body[:500],
                timestamp=date_match.group(1).strip() if date_match else "",
                source_file=source_file,
            ))

    return messages


def parse_plain_text(text: str, source_file: str = "") -> list[NormalizedMessage]:
    messages: list[NormalizedMessage] = []
    # Try to detect conversational patterns like "Name: message"
    conv_pattern = re.compile(r"^([A-Za-z][\w\s]{0,20}):\s+(.+)")

    for i, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        m = conv_pattern.match(line)
        if m:
            messages.append(NormalizedMessage(
                sender=m.group(1).strip(),
                text=m.group(2).strip(),
                source_file=source_file,
                line_number=i,
            ))
        else:
            # Treat each line as a message from unknown sender
            messages.append(NormalizedMessage(
                sender="Unknown",
                text=line,
                source_file=source_file,
                line_number=i,
            ))

    return messages


def extract_pdf_text(file_path: str | Path) -> str:
    """Extract text from a PDF file using pypdf."""
    from pypdf import PdfReader

    reader = PdfReader(str(file_path))
    pages: list[str] = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text.strip())
    return "\n\n".join(pages)


def parse_pdf(text: str, source_file: str = "") -> list[NormalizedMessage]:
    """Parse extracted PDF text into NormalizedMessage paragraphs."""
    messages: list[NormalizedMessage] = []
    # Split on double-newlines to get paragraphs / sections
    paragraphs = re.split(r"\n{2,}", text)
    for i, para in enumerate(paragraphs, 1):
        para = para.strip()
        if not para or len(para) < 10:
            continue
        # Collapse internal whitespace
        para = re.sub(r"\s+", " ", para)
        messages.append(NormalizedMessage(
            sender="Document",
            text=para[:500],
            source_file=source_file,
            line_number=i,
        ))
    return messages


def parse_file(text: str, filename: str = "") -> tuple[FileFormat, list[NormalizedMessage]]:
    fmt = detect_format(text, filename)
    parsers = {
        FileFormat.WHATSAPP: parse_whatsapp,
        FileFormat.EMAIL: parse_email,
        FileFormat.IMESSAGE: parse_imessage,
        FileFormat.PLAIN_TEXT: parse_plain_text,
        FileFormat.PDF: parse_pdf,
    }
    messages = parsers[fmt](text, source_file=filename)
    return fmt, messages
