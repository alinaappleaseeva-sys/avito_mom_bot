import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.vps_agent.tools import compare_candidates
from agents.vps_agent.config import SCORING_WEIGHTS

def test_compare_candidates():
    candidates = [
        {
            "provider": "Selectel",
            "name": "Exp-1",
            "billing_model": "pay_as_you_go",
            "approx_cost_for_3_months": 2000
        },
        {
            "provider": "RUVDS",
            "name": "Cheap-1",
            "billing_model": "monthly",
            "approx_cost_for_3_months": 900
        }
    ]
    
    # Selectel logic: 100 - (2000 * 0.01) + 20 (payasgo) + 10 (priority) = 100 - 20 + 30 = 110
    # RUVDS logic: 100 - (900 * 0.01) + 0 + 0 = 100 - 9 = 91
    # Selectel should win despite being more expensive.
    
    result = compare_candidates(candidates)
    assert result["provider"] == "Selectel", f"Expected Selectel, got {result.get('provider')}"
    print("✅ test_compare_candidates: Selectel won correctly due to PAYG and priority bonus.")

if __name__ == "__main__":
    test_compare_candidates()
