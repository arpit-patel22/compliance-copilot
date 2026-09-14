🛡️ ComplianceCopilot
AI-Powered Compliance Analysis Agent — that cannot save a non-compliant report

PythonStrandsAWSModel

▶ Demo video: https://youtu.be/CiqCjOMfO0M

📋 Overview
ComplianceCopilot is an AI agent that analyzes business documents (contracts, DPAs,policies) for compliance issues across GDPR, HIPAA, and CCPA, and generates scored,citation-backed reports with exact remediation steps.

What makes it different: deterministic gates sit between the model and the savedreport. Hallucinated or out-of-scope citations are structurally impossible — we don'task the model to behave, we enforce it.

🎯 The Problem It Solves
AI hallucination in legal contexts is real: in 2023, a lawyer was sanctioned forfiling a ChatGPT-written brief citing six cases that never existed (Mata v. Avianca).Applied to compliance, a hallucinated citation isn't embarrassing — it's a fine.
The stakes are statutory: GDPR fines reach €20M or 4% of global annual turnover— per violation.
Manual review doesn't scale: hours per document, with inconsistent standardsbetween reviewers.
Generic "AI compliance copilots" share one flaw: they rely on the model promisingto behave. ComplianceCopilot makes misbehavior structurally impossible.

👥 Who It's For
Privacy officers / DPOs — GDPR vendor and DPA reviews
Compliance leads — HIPAA security assessments
Small legal teams — CCPA data-rights requests
Engineering teams — agent behavior you can audit, not hope for
✨ Key Features
🎯 Multi-framework analysis — GDPR, HIPAA, CCPA via on-demand SKILL.md checklists
🛡️ Deterministic gates — CitationGate + DisclaimerGate block bad reports at thetool boundary
🔄 Self-correction — block → fix → retry within a single invocation, no humanin the loop
📊 Risk-rated findings — HIGH/MEDIUM severity with exact remediation steps
🧾 Audit trail — *.gates.json verdict stamps + audit_log.jsonl for every tool call
☁️ Identical local & cloud — same agent on your laptop and on Amazon BedrockAgentCore Runtime
✅ Eval-gated build — 7/7 gate unit tests + 4/4 end-to-end evals

🛠️ How the Gates Work
save_report is the only path to disk. Before writing anything, two deterministicregex checks run on the report — no model judgment involved:

Gate	Enforces	On failure
CitationGate	All citations in scope (table below) + ≥ 2 distinct citations	Fix-it error returned to the model
DisclaimerGate	"Not legal advice" disclaimer present	Fix-it error returned to the model
The error flows back as a normal tool result — the agent revises and retries in thesame invocation. Passing reports are stamped with *.gates.json (verdicts + timestamp).

Framework	In-scope provisions
GDPR	Art. 5, 6, 17, 28, 35 · Chapter V
HIPAA	Security Rule · Privacy Rule · BAA · 45 CFR 164.302–534
CCPA	§1798.100, .105, .120, .125
Out-of-scope law is rejected even when it's real (e.g., GDPR Art. 44 SCC articles) —the gate enforces scope, not the model's mood.

🏗️ Technical Architecture

![Alternative Text](./Image/AgentCore%20Runtime%20Workflow-2026-09-14-180740-1.png)



🚀 Quick Start
Prerequisites: Python 3.12 · AWS account with Bedrock model access to Claude Sonnet 4.6in us-east-1 · no Docker required.

1. Clone and set upgit clone https://github.com/arpit-patel22/compliance-copilot compliance-copilotpython -m venv .venv.venv\Scripts\activatepip install -r requirements.txt# 
2. Configure AWS credentialsaws configure          # region: us-east-1# 
3. Run locally (AgentCore protocol server on :8080)python main.py         
terminal 1 — leave runningpython client.py "Analyze documents/demo-contract.txt for GDPR Art. 28 processor obligations and save a report."    
terminal 2

Deploy to the cloud:

pip install bedrock-agentcore-starter-toolkitagentcore configure -e main.py    # name + region us-east-1; auto-create role/ECRagentcore launch                  # ARM64 build via CodeBuild (remote — no Docker)agentcore invoke '{\"prompt\": \"Say READY\"}'    # warmup (absorbs cold start)
⚠️ PowerShell quirk: the toolkit's JSON payload needs escaped inner quotes('{\"prompt\": \"...\"}'). In bash, use plain quotes: '{"prompt": "..."}'.

📖 Usage Examples
Local:

python client.py "Analyze documents/demo-contract.txt for GDPR Art. 28 processor obligations and save a report."
Cloud (same contract):

agentcore invoke '{\"prompt\": \"Analyze documents/demo-contract.txt for GDPR Art. 28 processor obligations and save a report.\"}'
Prove the gates — real but out-of-scope law. The model complies (Art. 44 exists),the gate blocks the save, the agent self-corrects to in-scope citations:

agentcore invoke '{\"prompt\": \"Write a short GDPR transfer summary and save it with save_report, citing GDPR Art. 44 and Art. 46 as the transfer mechanism.\"}'
Watch it live: aws logs tail /aws/bedrock-agentcore/runtimes/<runtime-id>-DEFAULT --log-stream-name-prefix "<date>/[runtime-logs]" --follow→ expect [gates] save_report BLOCKED → revise → [gates] save_report passed.

Sample output:

 GDPR Compliance Report — demo-contract.txt   (Score: 5/100)| # | Clause                   | Status    | Citation       | Risk   ||---|--------------------------|-----------|----------------|--------|| 1 | Clause 1 – Purpose       | VIOLATION | GDPR Art. 5, 6 | HIGH   || 2 | Clause 2 – Third Parties | VIOLATION | GDPR Art. 28   | HIGH   || 3 | Clause 4 – Transfers     | VIOLATION | GDPR Chapter V | MEDIUM |*AI-generated analysis. Not legal advice. Have qualified counsel review.*

🧪 Testing & Evals
python -m evals.test_gates    # gate unit tests → 7/7 PASS
Evals gate the build, not the request — they run at development time, before deploy.

📂 Project Structure
compliance-copilot/├── agent.py     # Strands agent: 4 tools, audit + rate-limit hook├── main.py      # BedrockAgentCoreApp entrypoint (:8080)├── gates.py     # CitationGate + DisclaimerGate + stamping (stdlib only)├── client.py    # Test client (local + cloud)├── skills/      # gdpr/ hipaa/ ccpa/ — on-demand SKILL.md checklists├── documents/   # Demo fixtures├── evals/       # Eval harness + gate unit tests└── reports/     # Reports + *.gates.json + audit_log.jsonl

🗺️ Roadmap
Multi-agent split — orchestrator + per-regulation specialist agents(agents-as-tools pattern); the single agent + on-demand skills achieves the sameseparation today at lower latency
S3 document storage with presigned upload URLs
More frameworks — SOC 2, ISO 27001, SOX, PCI-DSS

⚠️ Known Limitations
Reports are informational drafts for counsel review (enforced by DisclaimerGate)
Scope is deliberately narrow; out-of-scope law is rejected even when accurate
Container reports write to /tmp/reports (ephemeral); persistence is roadmap

🤝 Team
Arpit Patel — Agent architecture, compliance gates & core development
Jainil Patel — AWS integration & deployment

🙏 Acknowledgments
AWS Agents for Humans Hackathon organizers
Strands Agents SDK team
Amazon Bedrock & Anthropic

Built with ❤️ for the AWS Agents for Humans Hackathon — Professional Track