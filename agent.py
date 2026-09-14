import os, json
from strands import Agent, tool
from strands.models import BedrockModel
from strands.session.file_session_manager import FileSessionManager
from strands.hooks import BeforeToolCallEvent
from pathlib import Path
from gates import gate_error_message, write_gate_stamp
import time
from datetime import datetime, timezone


MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-6")
REGION = os.getenv("AWS_REGION", "us-east-1")
REPORTS_DIR = Path(os.environ.get("REPORTS_DIR", Path(__file__).parent / "reports"))

# ---------------- TOOLS ----------------

@tool
def read_document(path: str) -> str:
    """Read a .txt document from the documents/ folder and return its full text."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

@tool
def search_clauses(document_text: str, keywords: str) -> list:
    """Split a document into clauses (paragraphs) and return those containing any keyword.
    Args:
        document_text: full document text
        keywords: comma-separated terms, e.g. 'personal data,consent,erasure'
    """
    kws = [k.strip().lower() for k in keywords.split(",") if k.strip()]
    clauses = [p.strip() for p in document_text.split("\n\n") if p.strip()]
    hits = []
    for i, clause in enumerate(clauses, start=1):
        matched = [k for k in kws if k in clause.lower()]
        if matched:
            hits.append({"clause_number": i, "matched_keywords": matched, "text": clause})
    return hits

@tool
def load_skill(regulation: str) -> str:
    """Load the analysis procedure (SKILL.md) for a regulation: gdpr, hipaa, or ccpa."""
    path = os.path.join(os.path.dirname(__file__), "skills", regulation.lower(), "SKILL.md")
    if not os.path.exists(path):
        return f"No skill found for '{regulation}'. Supported: gdpr, hipaa, ccpa."
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

@tool
def save_report(report_markdown: str, document_name: str) -> str:
    """Saves a markdown compliance report into reports/ and returns the file path."""
    # --- GATES: block -> fix -> retry ---
    error = gate_error_message(report_markdown)
    if error:
        print("[gates] save_report BLOCKED")
        return error                       # model sees violations, self-corrects, retries
    print("[gates] save_report passed citation+disclaimer")

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)                      # was: os.makedirs("reports", ...)
    safe = document_name.rsplit(".", 1)[0].replace("/", "_").replace("\\", "_")
    out = REPORTS_DIR / f"{safe}-compliance-report.md"                  # was: os.path.join("reports", ...)
    with open(out, "w", encoding="utf-8") as f:
        f.write(report_markdown)

    write_gate_stamp(out)                  # audit stamp: <stem>.gates.json next to the report

    return str(out)     # keep it — likely `return str(out)

# ---------------- HOOKS: audit log + rate limiter ----------------

AUDIT_LOG = REPORTS_DIR / "audit_log.jsonl"          # anchored, platform-aware
MAX_TOOL_CALLS_PER_MINUTE = 60
_tool_call_times: list[float] = []                   # rolling window for rate limit


def audit_and_limit(event: BeforeToolCallEvent):
    tool_name = event.tool_use["name"]

    # ---- 1. RATE LIMIT (enforcement) — must run OUTSIDE the try block,
    #         because event.interrupt() works by raising an interrupt ----
    now = time.time()
    while _tool_call_times and now - _tool_call_times[0] > 60:
        _tool_call_times.pop(0)
    _tool_call_times.append(now)
    if len(_tool_call_times) > MAX_TOOL_CALLS_PER_MINUTE:
        event.interrupt(
            "rate_limit",
            f"Rate limit exceeded: more than {MAX_TOOL_CALLS_PER_MINUTE} tool calls in 60s.",
        )

    # ---- 2. AUDIT LOG (observability) — may never crash an invocation ----
    try:
        AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "tool": tool_name,
            "input_keys": sorted((event.tool_use.get("input") or {}).keys()),
        }
        with open(AUDIT_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError as e:
        print(f"[audit] log write failed (non-fatal): {e}")

# ---------------- AGENT ----------------

SYSTEM_PROMPT = """You are ComplianceCopilot, an AI compliance analysis assistant.

WORKFLOW for every analysis:
1. read_document to load the document.
2. load_skill for EACH regulation requested. Follow its procedure exactly.
3. search_clauses using the keywords the skill specifies.
4. Judge each clause YOURSELF: compliant / violation / unclear — cite the exact
   article (e.g. 'GDPR Art. 17'), assign risk HIGH/MEDIUM/LOW, write a one-line fix.
5. save_report with a markdown report: summary, score /100, findings table,
   and ALWAYS this disclaimer: 'AI-generated analysis. Not legal advice.
   Have qualified counsel review.'

RULES:
- NEVER state a finding without a regulation citation.
- If no skill exists for a requested regulation, say so instead of guessing.
- Be concise. Output reports in markdown.
- Do not use emoji in reports; use plain text markers like [HIGH], [MEDIUM], [LOW].
- If no skill exists for a requested regulation, say so instead of guessing"""

compliance_agent = Agent(
    model=BedrockModel(model_id=MODEL_ID, region_name=REGION, temperature=0.2),
    tools=[read_document, search_clauses, load_skill, save_report],
    system_prompt=SYSTEM_PROMPT,
    session_manager=FileSessionManager(session_id="analyst-001", base_dir="./sessions"),
    callback_handler=None, 
)
compliance_agent.add_hook(audit_and_limit)

if __name__ == "__main__":
    result = compliance_agent("Analyze documents/demo-contract.txt for HIPAA and CCPA compliance. " \
    "Save one combined report.")
    print(result)