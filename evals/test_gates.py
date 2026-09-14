"""Gate unit tests. Run: python -m evals.test_gates"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gates import DISCLAIMER, citation_gate, disclaimer_gate, gate_error_message, run_gates

GOOD = f"""# Vendor DPIA Screening
Processing relies on legitimate interests under GDPR Art. 6(1)(f); transfers
to the sub-processor follow GDPR Chapter V SCCs.

{DISCLAIMER}
"""

def test_good_report_passes(): assert run_gates(GOOD) == []

def test_missing_disclaimer_blocked():
    assert any("DisclaimerGate" in v for v in disclaimer_gate("Clean report citing GDPR Art. 6 and CCPA 1798.105."))

def test_hallucinated_gdpr_blocked():
    v = citation_gate(f"Under GDPR Art. 27 the appointee must be established in the EU. {DISCLAIMER}")
    assert v and any("27" in x for x in v)

def test_hallucinated_ccpa_blocked():
    v = citation_gate(f"Per CCPA 1798.121 consumers may opt out. See also GDPR Art. 5. {DISCLAIMER}")
    assert any("1798.121" in x for x in v)

def test_too_few_citations_blocked():
    v = citation_gate(f"A perfectly worded report with zero citations. {DISCLAIMER}")
    assert any("distinct in-scope citation" in x for x in v)

def test_gate_error_message_blocks():
    err = gate_error_message("no cites, no disclaimer")
    assert err is not None and "BLOCKED" in err

def test_gate_error_message_allows_good_report():
    assert gate_error_message(GOOD) is None

if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    failed = []
    for n, f in tests:
        try:
            f()
        except Exception as e:
            failed.append(f"{n}: {e}")
    print(f"gates: {len(tests) - len(failed)}/{len(tests)} PASS")
    for x in failed:
        print("FAIL:", x)
    sys.exit(1 if failed else 0)