#!/usr/bin/env python3
"""
Test: Ayesha IO Boost via MBD4 Hypermutator Inference
=====================================================
Verify that Ayesha's MBD4 mutation triggers IO boost even without measured TMB.

Author: Zo
Date: January 2025
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "oncology-coPilot" / "oncology-backend-minimal"))

from api.services.efficacy_orchestrator.sporadic_gates import apply_sporadic_gates


def test_ayesha_mbd4_io_boost():
    """
    Test that Ayesha's MBD4 mutation triggers IO boost.
    
    Ayesha's profile:
    - MBD4 homozygous pathogenic (germline)
    - TMB: UNKNOWN (no NGS)
    - MSI: MSS (preserved MMR)
    - PD-L1 CPS: 10
    
    Expected: Pembrolizumab should get 1.25x boost via hypermutator inference
    """
    print("=" * 70)
    print("TEST: Ayesha MBD4 → IO Boost via Hypermutator Inference")
    print("=" * 70)
    
    # Ayesha's tumor context (no TMB, MSS, but has MBD4)
    tumor_context = {
        "msi_status": "MSS",  # NOT MSI-H
        "tmb": None,  # Unknown!
        "completeness_score": 0.5,
        "pd_l1_cps": 10,
        # Germline mutations nested in tumor_context
        "germline": {
            "status": "POSITIVE",
            "mutations": [
                {
                    "gene": "MBD4",
                    "variant": "c.1293delA",
                    "protein_change": "p.K431Nfs*54",
                    "classification": "pathogenic"
                },
                {
                    "gene": "PDGFRA",
                    "variant": "c.2263T>C",
                    "classification": "VUS"
                }
            ]
        }
    }
    
    # Also test with germline_mutations as separate parameter
    germline_mutations = [
        {"gene": "MBD4", "classification": "pathogenic"},
        {"gene": "PDGFRA", "classification": "VUS"}
    ]
    
    # Test checkpoint inhibitor (Pembrolizumab)
    print("\n--- Pembrolizumab (Checkpoint Inhibitor) ---")
    efficacy, confidence, rationale = apply_sporadic_gates(
        drug_name="Pembrolizumab",
        drug_class="checkpoint_inhibitor",
        moa="anti-pd1",
        efficacy_score=0.5,
        confidence=0.7,
        germline_status="positive",  # MBD4 positive
        tumor_context=tumor_context,
        germline_mutations=germline_mutations
    )
    
    print(f"Input efficacy: 0.5")
    print(f"Output efficacy: {efficacy:.3f}")
    print(f"Boost applied: {efficacy / 0.5:.2f}x")
    print(f"\nRationale:")
    for r in rationale:
        gate = r.get("gate", "")
        reason = r.get("reason", "")
        if gate and reason:
            print(f"  [{gate}] {reason}")
    
    # Check if hypermutator inference was triggered
    hypermutator_gate = next((r for r in rationale if r.get("gate") == "IO_HYPERMUTATOR_INFERENCE"), None)
    
    if hypermutator_gate:
        print("\n✅ PASS: Hypermutator inference triggered!")
        print(f"   Genes detected: {hypermutator_gate.get('hypermutator_genes')}")
        print(f"   Boost: {hypermutator_gate.get('boost')}x")
        assert abs(efficacy - 0.625) < 0.01, f"Expected 0.625, got {efficacy}"
        return True
    else:
        print("\n❌ FAIL: Hypermutator inference NOT triggered!")
        return False


def test_no_boost_without_hypermutator():
    """
    Test that patients without hypermutator genes don't get inferred boost.
    """
    print("\n" + "=" * 70)
    print("TEST: No Hypermutator → No Inferred Boost")
    print("=" * 70)
    
    tumor_context = {
        "msi_status": "MSS",
        "tmb": None,  # Unknown
        "completeness_score": 0.5,
        # NO hypermutator genes
        "mutations": [
            {"gene": "TP53", "classification": "pathogenic"}
        ]
    }
    
    efficacy, confidence, rationale = apply_sporadic_gates(
        drug_name="Pembrolizumab",
        drug_class="checkpoint_inhibitor",
        moa="anti-pd1",
        efficacy_score=0.5,
        confidence=0.7,
        germline_status="negative",
        tumor_context=tumor_context
    )
    
    print(f"Input efficacy: 0.5")
    print(f"Output efficacy: {efficacy:.3f}")
    
    hypermutator_gate = next((r for r in rationale if r.get("gate") == "IO_HYPERMUTATOR_INFERENCE"), None)
    
    if hypermutator_gate is None:
        print("✅ PASS: No hypermutator inference (as expected)")
        assert abs(efficacy - 0.5) < 0.01, f"Expected 0.5, got {efficacy}"
        return True
    else:
        print("❌ FAIL: Hypermutator inference triggered incorrectly!")
        return False


def test_measured_tmb_takes_priority():
    """
    Test that measured TMB takes priority over hypermutator inference.
    """
    print("\n" + "=" * 70)
    print("TEST: Measured TMB Takes Priority")
    print("=" * 70)
    
    tumor_context = {
        "msi_status": "MSS",
        "tmb": 25,  # Measured TMB-HIGH!
        "completeness_score": 0.7,
        "germline": {
            "mutations": [
                {"gene": "MBD4", "classification": "pathogenic"}
            ]
        }
    }
    
    efficacy, confidence, rationale = apply_sporadic_gates(
        drug_name="Pembrolizumab",
        drug_class="checkpoint_inhibitor",
        moa="anti-pd1",
        efficacy_score=0.5,
        confidence=0.7,
        germline_status="positive",
        tumor_context=tumor_context
    )
    
    print(f"Input efficacy: 0.5")
    print(f"Output efficacy: {efficacy:.3f}")
    
    tmb_gate = next((r for r in rationale if r.get("gate") == "IO_TMB_BOOST"), None)
    hypermutator_gate = next((r for r in rationale if r.get("gate") == "IO_HYPERMUTATOR_INFERENCE"), None)
    
    if tmb_gate and not hypermutator_gate:
        print("✅ PASS: Measured TMB boost (1.35x) takes priority over hypermutator inference")
        assert abs(efficacy - 0.675) < 0.01, f"Expected 0.675, got {efficacy}"
        return True
    else:
        print("❌ FAIL: Priority not working correctly!")
        return False


def test_pole_pold1_hypermutator():
    """
    Test POLE/POLD1 hypermutator genes also trigger inference.
    """
    print("\n" + "=" * 70)
    print("TEST: POLE/POLD1 Hypermutator Inference")
    print("=" * 70)
    
    for gene in ["POLE", "POLD1"]:
        tumor_context = {
            "msi_status": "MSS",
            "tmb": None,
            "completeness_score": 0.5,
            "mutations": [
                {"gene": gene, "classification": "pathogenic"}
            ]
        }
        
        efficacy, confidence, rationale = apply_sporadic_gates(
            drug_name="Pembrolizumab",
            drug_class="checkpoint_inhibitor",
            moa="anti-pd1",
            efficacy_score=0.5,
            confidence=0.7,
            germline_status="negative",
            tumor_context=tumor_context
        )
        
        hypermutator_gate = next((r for r in rationale if r.get("gate") == "IO_HYPERMUTATOR_INFERENCE"), None)
        
        if hypermutator_gate and gene in hypermutator_gate.get("hypermutator_genes", []):
            print(f"  ✅ {gene}: Triggered inference (boost {hypermutator_gate.get('boost')}x)")
        else:
            print(f"  ❌ {gene}: Failed to trigger inference")
            return False
    
    return True


def main():
    print("=" * 70)
    print("IO HYPERMUTATOR INFERENCE TEST SUITE")
    print("=" * 70)
    
    results = []
    
    results.append(("Ayesha MBD4 IO Boost", test_ayesha_mbd4_io_boost()))
    results.append(("No Boost Without Hypermutator", test_no_boost_without_hypermutator()))
    results.append(("Measured TMB Priority", test_measured_tmb_takes_priority()))
    results.append(("POLE/POLD1 Hypermutator", test_pole_pold1_hypermutator()))
    
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🔥 ALL TESTS PASSED! IO hypermutator inference is production-ready.")
    else:
        print("\n⚠️ Some tests failed. Review output above.")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
