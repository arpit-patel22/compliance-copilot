import os, json
from strands import Agent, tool
from strands.models import BedrockModel
from strands.session.file_session_manager import FileSessionManager
from strands.hooks import BeforeToolCallEvent

MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-6")
REGION = os.getenv("AWS_REGION", "us-east-1")

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
    """Save a markdown compliance report into reports/ and return the file path."""
    os.makedirs("reports", exist_ok=True)
    safe = document_name.rsplit(".", 1)[0].replace("/", "_").replace("\\", "_")
    out = os.path.join("reports", f"{safe}-compliance-report.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write(report_markdown)
    return out

# ---------------- HOOKS: audit log + rate limiter ----------------

AUDIT_LOG = "audit_log.jsonl"
_tool_counts: dict = {}

def audit_and_limit(event: BeforeToolCallEvent):
    """Deterministic safety layer: log every tool call, stop runaway loops."""
    name = event.tool_use["name"]
    with open(AUDIT_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps({"tool": name}) + "\n")
    _tool_counts[name] = _tool_counts.get(name, 0) + 1
    if _tool_counts[name] > 15:
        event.interrupt("rate_limit",
            reason=f"Tool '{name}' exceeded 15 calls — stopping possible loop.")

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