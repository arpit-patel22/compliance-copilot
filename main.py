import os
from pathlib import Path

os.environ.setdefault(
    "REPORTS_DIR",
    "/tmp/reports" if os.name != "nt" else "reports",   # container vs Windows
)

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from agent import compliance_agent                                # your wired agent: hooks + gates included

DOCS_DIR = Path(__file__).parent / "documents"
app = BedrockAgentCoreApp()

@app.entrypoint
def invoke(payload: dict) -> dict:
    # inline document support (from our earlier change) — travels in the request
    doc = payload.get("document")
    if isinstance(doc, dict) and doc.get("filename") and doc.get("content"):
        DOCS_DIR.mkdir(parents=True, exist_ok=True)
        (DOCS_DIR / doc["filename"]).write_text(doc["content"], encoding="utf-8")

    result = compliance_agent(payload.get("prompt", ""))
    return {"result": str(getattr(result, "output", result))}

if __name__ == "__main__":
    app.run()   # serves 0.0.0.0:8080 locally AND in the container