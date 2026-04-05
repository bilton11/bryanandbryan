"""
AI Output Guardrail — Bryan and Bryan

Strips directive language from AI-generated text and replaces it with statistical
framing. All patterns must be reviewed by supervising lawyer before any user-facing
AI feature ships.

This module is the single enforcement point for the "legal information, not legal
advice" constraint applied to all AI-generated output in the application.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class GuardrailStatus(Enum):
    PASSED = "PASSED"          # No directive language found — output unchanged
    TRANSFORMED = "TRANSFORMED"  # Directive language replaced with statistical framing
    BLOCKED = "BLOCKED"        # Output was empty or became empty after processing


@dataclass
class GuardrailResult:
    status: GuardrailStatus
    text: str        # Processed (safe) text for display
    original: str    # Raw input before processing


# Directive language patterns and their statistical replacements.
# Each pattern is marked LAWYER_REVIEW_REQUIRED — these substitutions must be
# reviewed by the supervising lawyer before any user-facing AI feature ships.
DIRECTIVE_PATTERNS: list[tuple[str, str]] = [
    (r'\byou should\b', 'cases with similar characteristics typically'),    # LAWYER_REVIEW_REQUIRED
    (r'\byou must\b', 'the procedure requires'),                            # LAWYER_REVIEW_REQUIRED
    (r'\byou need to\b', 'the process involves'),                           # LAWYER_REVIEW_REQUIRED
    (r'\bI recommend\b', 'statistically'),                                  # LAWYER_REVIEW_REQUIRED
    (r'\bmy advice\b', 'based on similar cases'),                           # LAWYER_REVIEW_REQUIRED
    (r'\byou will win\b', 'cases with these characteristics have'),         # LAWYER_REVIEW_REQUIRED
    (r'\byou will lose\b', 'cases with these characteristics have'),        # LAWYER_REVIEW_REQUIRED
    (r'\byour case is strong\b', 'cases with these characteristics tend to'),  # LAWYER_REVIEW_REQUIRED
    (r'\byour case is weak\b', 'cases with these characteristics tend to'),    # LAWYER_REVIEW_REQUIRED
]

_BLOCKED_TEXT = "Assessment unavailable for this case. Please consult a lawyer."


class AIGuardrail:
    """
    Processes raw AI output and enforces statistical framing.

    Usage:
        from app.services.ai_guardrail import guardrail
        result = guardrail.process(raw_ai_text)
        if result.status != GuardrailStatus.BLOCKED:
            display(result.text)
    """

    def process(self, raw_output: str) -> GuardrailResult:
        """
        Run all directive language patterns against raw_output.

        Returns:
            GuardrailResult with status PASSED, TRANSFORMED, or BLOCKED.
            BLOCKED is returned when input is empty or whitespace-only.
        """
        original = raw_output

        # Block empty or whitespace-only input immediately
        if not raw_output or not raw_output.strip():
            return GuardrailResult(
                status=GuardrailStatus.BLOCKED,
                text=_BLOCKED_TEXT,
                original=original,
            )

        transformed = False
        text = raw_output

        for pattern, replacement in DIRECTIVE_PATTERNS:
            new_text, count = re.subn(pattern, replacement, text, flags=re.IGNORECASE)
            if count > 0:
                transformed = True
                text = new_text

        # If processing somehow produced empty output, block it
        if not text or not text.strip():
            return GuardrailResult(
                status=GuardrailStatus.BLOCKED,
                text=_BLOCKED_TEXT,
                original=original,
            )

        status = GuardrailStatus.TRANSFORMED if transformed else GuardrailStatus.PASSED
        return GuardrailResult(status=status, text=text, original=original)


# Module-level singleton — import and use directly
guardrail = AIGuardrail()
