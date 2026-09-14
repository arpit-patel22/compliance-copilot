"""
gates.py -- CitationGate + DisclaimerGate for ComplianceCopilot (FINAL).

Enforcement happens INSIDE save_report (no hooks):
  error = gate_error_message(report_markdown)
  if error: return error            # model sees violations, fixes, retries
  ...save...
  write_gate_stamp(out_path)        # drops <stem>.gates.json audit stamp

  DisclaimerGate: report must contain the not-legal-advice disclaimer.
  CitationGate:   citations must be in scope (GDPR Art 5/6/17/28/35 + Ch V;
                  HIPAA Security/Privacy Rule, BAA, 45 CFR 164.302-534;
                  CCPA 1798.100/.105/.120/.125) and >= MIN_DISTINCT_CITATIONS.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

MIN_DISTINCT_CITATIONS = 2

DISCLAIMER = (
    "This report is for informational purposes only and does not constitute "
    "legal advice."
)

_DISCLAIMER_RE = re.compile(
    r"not\s+(?:a\s+)?(?:(?:substitute\s+for|constitute)\s+)?legal\s+advice",
    re.IGNORECASE,
)

_GDPR_IN_SCOPE = {"5", "6", "17", "28", "35"}
_CCPA_IN_SCOPE = {"100", "105", "120", "125"}

_GDPR_ART_FWD = re.compile(r"\bGDPR\b(?:'s)?[\s-]{0,5}(?:Art(?:icle)?s?\.?\s*)?(\d{1,3})\b", re.I)
_GDPR_ART_REV = re.compile(r"\bArt(?:icle)?s?\.?\s*(\d{1,3})\b(?:\s*\([^)]*\))?\s*(?:of\s+the\s+)?GDPR\b", re.I)
_GDPR_CH_FWD  = re.compile(r"\bGDPR\b[\s-]{0,5}Chapter\s+([IVXivx]+|\d{1,2})\b", re.I)
_GDPR_CH_REV  = re.compile(r"\bChapter\s+([IVXivx]+|\d{1,2})\s+(?:of\s+the\s+)?GDPR\b", re.I)
_HIPAA_RULE   = re.compile(r"\bHIPAA\b(?:'s)?[\s-]{0,5}(Security|Privacy)\s+Rule\b", re.I)
_HIPAA_BAA    = re.compile(r"\bBAAs?\b|\bBusiness\s+Associate\s+Agreements?\b", re.I)
_HIPAA_CFR    = re.compile(r"\b45\s+CFR\s*§?\s*164\.(\d{1,3})\b", re.I)
_CCPA_SEC     = re.compile(r"\b1798\.(\d{1,3})\b")


def disclaimer_gate(report: str) -> list[str]:
    if _DISCLAIMER_RE.search(report):
        return []
    return [f"DisclaimerGate: missing required disclaimer. Add this exact sentence: \"{DISCLAIMER}\""]


def citation_gate(report: str) -> list[str]:
    problems: list[str] = []
    valid: set[str] = set()

    def check(token: str, matched: str, ok: bool, hint: str) -> None:
        if ok:
            valid.add(token)
        else:
            problems.append(f"CitationGate: '{matched}' is not in scope. {hint}")

    for rx in (_GDPR_ART_FWD, _GDPR_ART_REV):
        for m in rx.finditer(report):
            art = m.group(1)
            check(f"gdpr:{art}", m.group(0), art in _GDPR_IN_SCOPE,
                  "In-scope GDPR: Art. 5, 6, 17, 28, 35, Chapter V.")
    for rx in (_GDPR_CH_FWD, _GDPR_CH_REV):
        for m in rx.finditer(report):
            tok = m.group(1)
            check("gdpr:chapter_v", m.group(0), tok.upper() == "V" or tok == "5",
                  "In-scope GDPR chapters: Chapter V only.")
    for m in _HIPAA_RULE.finditer(report):
        valid.add(f"hipaa:{m.group(1).lower()}_rule")
    for m in _HIPAA_BAA.finditer(report):
        valid.add("hipaa:baa")
    for m in _HIPAA_CFR.finditer(report):
        sec = int(m.group(1))
        check(f"hipaa:164.{sec}", m.group(0), 302 <= sec <= 534,
              "HIPAA cites must be 45 CFR 164.302-164.534.")
    for m in _CCPA_SEC.finditer(report):
        sec = m.group(1)
        check(f"ccpa:1798.{sec}", m.group(0), sec in _CCPA_IN_SCOPE,
              "In-scope CCPA: 1798.100, 1798.105, 1798.120, 1798.125.")

    if len(valid) < MIN_DISTINCT_CITATIONS:
        problems.append(
            f"CitationGate: only {len(valid)} distinct in-scope citation(s) found; "
            f"need >= {MIN_DISTINCT_CITATIONS}."
        )
    return problems


def run_gates(report: str) -> list[str]:
    return disclaimer_gate(report) + citation_gate(report)


def format_violations(violations: list[str]) -> str:
    lines = ["save_report BLOCKED by compliance gates. Fix the report and call save_report again:"]
    lines += [f"- {v}" for v in violations]
    lines.append(f"- Required disclaimer sentence: \"{DISCLAIMER}\"")
    return "\n".join(lines)


def gate_error_message(report_text: str | None) -> str | None:
    """None = gates pass. Otherwise returns the fix-it error text for the model."""
    violations = run_gates(report_text or "")
    return format_violations(violations) if violations else None


def write_gate_stamp(report_path: str | Path) -> None:
    """Writes <stem>.gates.json next to the saved report."""
    p = Path(report_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    (p.parent / f"{p.stem}.gates.json").write_text(json.dumps({
        "citation_gate": "PASS",
        "disclaimer_gate": "PASS",
        "gated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }, indent=2), encoding="utf-8")