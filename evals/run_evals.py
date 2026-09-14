from strands_evals import Case, Experiment
from strands_evals.evaluators import OutputEvaluator
from agent import compliance_agent

cases = [
    Case(name="art17-erasure", 
         input="Analyze documents/demo-contract.txt for GDPR compliance. Reply with ONLY the findings table.",
         expected_output="Must flag the clause preventing data deletion as a violation citing GDPR Art. 17 with HIGH risk."),
    Case(name="art5-purpose",
         input="Analyze documents/demo-contract.txt for GDPR compliance. Reply with ONLY the findings table.",
         expected_output="Must flag 'any commercial purpose' as violating GDPR Art. 5 purpose limitation."),
    Case(name="art28-processors",
         input="Analyze documents/demo-contract.txt for GDPR compliance. Reply with ONLY the findings table.",
         expected_output="Must flag third-party sharing without safeguards citing GDPR Art. 28."),
    Case(name="ccpa-deletion",
         input="Analyze documents/demo-contract.txt for CCPA compliance. Reply with ONLY the findings table.",
         expected_output="Must flag denial of deletion citing CCPA §1798.105."),
    # Add 5-8 more: retention, transfers, hipaa safeguards, citation-format check, disclaimer check...
]

experiment = Experiment(cases=cases, evaluators=[OutputEvaluator()])
reports = experiment.run_evaluations(compliance_agent)
for r in reports:
    print(r)