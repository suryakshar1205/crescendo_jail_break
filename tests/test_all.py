"""
Master System Test Suite Entrypoint for Crescendo Jailbreak Defense.

Executes all 34 certified test cases across all subsystems in a single command:
1. tests/test_crs_pipeline.py          (Full Pipeline E2E & State Tracking)
2. tests/test_crs_boundaries.py        (Decision Thresholds & Risk Clamping)
3. tests/test_faiss_vector_store.py    (FAISS Engine, Search SLA & Persistence)
4. tests/regression/test_known_attacks.py (Attack Corpora & Synthetic Mutations)
5. tests/regression/test_benign_conversations.py (50 Benign Conversations)
6. tests/test_adaptive_adversary.py    (Jittering & Semantic Smuggling Evasions)
7. tests/test_session_isolation.py     (Multi-Session State Isolation & Reset)

Usage:
    python tests/test_all.py
    or:
    python -m unittest tests/test_all.py
"""
import os
import sys

# Prevent OpenMP runtime collision & headless matplotlib on Windows
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MPLBACKEND"] = "Agg"

import unittest

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


from tests.test_crs_pipeline import TestPRDPipelineIntegration
from tests.test_crs_boundaries import (
    TestExactDecisionBoundaries,
    TestScoreNormalizationAndRanges,
)
from tests.test_faiss_vector_store import TestFAISSVectorStore
from tests.regression.test_known_attacks import TestKnownAttacksRegression
from tests.regression.test_benign_conversations import TestBenignConversationsRegression
from tests.test_adaptive_adversary import TestAdaptiveAdversarySimulation
from tests.test_session_isolation import TestSessionIsolationAndReset


def load_master_suite() -> unittest.TestSuite:
    """Compiles all 34 certified master test cases directly from test classes."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    test_classes = [
        TestPRDPipelineIntegration,          # 6 tests
        TestExactDecisionBoundaries,         # 7 tests
        TestScoreNormalizationAndRanges,     # 4 tests
        TestFAISSVectorStore,                # 7 tests
        TestKnownAttacksRegression,          # 5 tests
        TestBenignConversationsRegression,   # 1 test
        TestAdaptiveAdversarySimulation,     # 2 tests
        TestSessionIsolationAndReset,        # 2 tests (Isolation & Reset)
    ]

    for tc in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(tc))

    return suite



def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    print("=" * 70)
    print("CRESCENDO JAILBREAK DEFENSE -- MASTER TEST SUITE (34 TESTS)")
    print("=" * 70)
    
    suite = load_master_suite()
    total_expected = suite.countTestCases()
    print(f"[+] Loaded {total_expected} master tests across all 6 modules.\n")

    runner = unittest.TextTestRunner(stream=sys.stdout, verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 70)
    print("MASTER TEST CERTIFICATION SUMMARY:")
    print(f"  * Total Tests Run : {result.testsRun}")
    print(f"  * Failures        : {len(result.failures)}")
    print(f"  * Errors          : {len(result.errors)}")
    print(f"  * Status          : {'ALL ' + str(result.testsRun) + ' TESTS PASSED (100% SUCCESS)' if result.wasSuccessful() else 'TEST FAILURES DETECTED'}")
    print("=" * 70)


    sys.exit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
