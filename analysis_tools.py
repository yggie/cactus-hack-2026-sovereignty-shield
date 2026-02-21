"""FunctionGemma tool schemas for document analysis."""

from __future__ import annotations

ANALYSIS_TOOLS = [
    {
        "name": "flag_threat",
        "description": "Flag a message that contains a direct or implied threat of violence, harm, intimidation, or coercion against a person.",
        "parameters": {
            "type": "object",
            "properties": {
                "quote": {
                    "type": "string",
                    "description": "The exact text from the message that contains the threat.",
                },
                "severity": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "critical"],
                    "description": "Severity: low=veiled/implied, medium=clear verbal threat, high=specific threat of action, critical=imminent danger.",
                },
                "explanation": {
                    "type": "string",
                    "description": "Brief explanation of why this is a threat and what kind.",
                },
            },
            "required": ["quote", "severity", "explanation"],
        },
    },
    {
        "name": "extract_timeline_event",
        "description": "Extract a significant event mentioned in the messages that should appear on a timeline for legal review. Events include incidents, meetings, payments, moves, or key conversations.",
        "parameters": {
            "type": "object",
            "properties": {
                "quote": {
                    "type": "string",
                    "description": "The relevant text describing the event.",
                },
                "date": {
                    "type": "string",
                    "description": "Date or approximate date of the event (from message timestamp or text).",
                },
                "event_summary": {
                    "type": "string",
                    "description": "One-sentence summary of what happened.",
                },
            },
            "required": ["quote", "date", "event_summary"],
        },
    },
    {
        "name": "identify_pattern",
        "description": "Identify a recurring behavioral pattern across messages, such as gaslighting, love-bombing, isolation tactics, financial control, or escalating aggression.",
        "parameters": {
            "type": "object",
            "properties": {
                "pattern_type": {
                    "type": "string",
                    "description": "Type of pattern: gaslighting, isolation, financial_control, love_bombing, escalation, manipulation, surveillance, other.",
                },
                "quote": {
                    "type": "string",
                    "description": "Representative quote illustrating this pattern.",
                },
                "severity": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "critical"],
                    "description": "Severity of the pattern.",
                },
                "explanation": {
                    "type": "string",
                    "description": "Explanation of the pattern and why it's concerning.",
                },
            },
            "required": ["pattern_type", "quote", "severity", "explanation"],
        },
    },
    {
        "name": "classify_communication",
        "description": "Classify the overall tone and dynamics of a communication chunk. Use when messages don't contain clear threats or patterns but the communication style is noteworthy.",
        "parameters": {
            "type": "object",
            "properties": {
                "tone": {
                    "type": "string",
                    "description": "Overall tone: hostile, manipulative, threatening, normal, supportive, distressed.",
                },
                "power_dynamic": {
                    "type": "string",
                    "description": "Observed power dynamic: balanced, one_sided_control, coercive, submissive_compliance, unclear.",
                },
                "quote": {
                    "type": "string",
                    "description": "Representative quote showing this dynamic.",
                },
                "explanation": {
                    "type": "string",
                    "description": "Brief explanation of the communication classification.",
                },
            },
            "required": ["tone", "power_dynamic", "quote", "explanation"],
        },
    },
    {
        "name": "flag_scam_indicator",
        "description": "Flag messages that contain scam indicators: requests for money, urgency pressure, impersonation, phishing links, advance fee fraud, or romance scam patterns.",
        "parameters": {
            "type": "object",
            "properties": {
                "scam_type": {
                    "type": "string",
                    "description": "Type of scam: phishing, romance_scam, advance_fee, impersonation, investment_fraud, other.",
                },
                "quote": {
                    "type": "string",
                    "description": "The exact text showing the scam indicator.",
                },
                "severity": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "critical"],
                    "description": "Severity: low=suspicious, medium=likely scam, high=clear scam, critical=imminent financial danger.",
                },
                "explanation": {
                    "type": "string",
                    "description": "Explanation of the scam indicator.",
                },
            },
            "required": ["scam_type", "quote", "severity", "explanation"],
        },
    },
    {
        "name": "no_findings",
        "description": "Indicate that the analyzed messages contain no concerning content. Use this when the conversation chunk appears normal with no threats, scams, abuse patterns, or notable events.",
        "parameters": {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "Brief summary of what the messages contain (e.g., 'casual conversation about weekend plans').",
                },
            },
            "required": ["summary"],
        },
    },
]

# Map tool names to finding categories for DB storage
TOOL_TO_CATEGORY = {
    "flag_threat": "threat",
    "identify_pattern": "pattern",
    "classify_communication": "communication",
    "flag_scam_indicator": "scam",
    "extract_timeline_event": "timeline_event",
}

# Tools that are part of the analysis set (for routing detection)
ANALYSIS_TOOL_NAMES = {t["name"] for t in ANALYSIS_TOOLS}
