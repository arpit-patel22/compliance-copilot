import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strands_evals import Case, Experiment
from strands_evals.evaluators import OutputEvaluator
from agent import compliance_agent

RUBRIC = """Judge the agent's compliance analysis response:
1. Citation check: every violation finding must include a specific regulation citation (e.g., "GDPR Art. 17"). Missing citations = fail.
2. Risk check: each finding must include a risk level (HIGH/MEDIUM/LOW).
3. Substance check: the expected violation described in this case must be identified.
Score PASS only if criteria 1-3 are all met."""

def _to_prompt(x):
    """Recursively extract a plain prompt string from any input shape."""
    if isinstance(x, str):
        return x
    if isinstance(x, dict):
        for key in ("prompt", "input", "text", "query"):
            if isinstance(x.get(key), str):
                return x[key]
        content = x.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and isinstance(block.get("text"), str):
                    return block["text"]
        return str(x)
    if isinstance(x, (list, tuple)):
        for item in x:
            found = _to_prompt(item)
            if found and found != str(x):
                return found
        return str(x)
    return str(x)

def compliance_task(case_input):
    """Adapter: the harness may pass str / dict / message-list — normalize it."""
    print(f"[adapter] harness passed: {type(case_input).__name__}")
    prompt = _to_prompt(case_input)
    result = compliance_agent(prompt)
    return str(result)

cases = [
    Case(name="art17-erasure",
         input="Analyze documents/demo-contract.txt for GDPR compliance. Reply with ONLY the findings table.",
         expected_output="The findings must flag the clause preventing data deletion as a violation citing GDPR Art. 17 with HIGH risk."),
    Case(name="art5-purpose",
         input="Analyze documents/demo-contract.txt for GDPR compliance. Reply with ONLY the findings table.",
         expected_output="The findings must flag 'any commercial purpose' as violating GDPR Art. 5 purpose limitation with HIGH risk."),
    Case(name="art28-processors",
         input="Analyze documents/demo-contract.txt for GDPR compliance. Reply with ONLY the findings table.",
         expected_output="The findings must flag third-party sharing without safeguards citing GDPR Art. 28."),
    Case(name="ccpa-deletion",
         input="Analyze documents/demo-contract.txt for CCPA compliance. Reply with ONLY the findings table.",
         expected_output="The findings must flag denial of deletion citing CCPA S1798.105."),
]

experiment = Experiment(cases=cases, evaluators=[OutputEvaluator(rubric=RUBRIC)])
reports = experiment.run_evaluations(compliance_task)
for r in reports:
    print(r)