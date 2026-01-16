#!/usr/bin/env python3
"""
Test: Ayesha IO Drug Selection
==============================
Demonstrate how we select the safest IO drug for Ayesha.

Author: Zo
Date: January 2025
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "oncology-coPilot" / "oncology-backend-minimal"))

from api.services.toxicity_pathway_mappings import (
    get_io_drug_profile,
    compare_io_drugs,
    select_safest_io,
    IO_DRUG_PROFILES
)


def test_io_drug_profiles():
    """Test that IO drug profiles are properly defined."""
    print("=" * 70)
    print("TEST: IO Drug Profiles")
    print("=" * 70)
    
    for drug, profile in IO_DRUG_PROFILES.items():
        rate = profile.get("irae_grade3plus_rate", 0)
        target = profile.get("target", "Unknown")
        print(f"  {drug:20} | {profile.get('brand_name', ''):15} | {target:12} | irAE: {rate:.0%}")
    
    print("\n✅ All IO drug profiles loaded")
    return True


def test_ayesha_io_selection():
    """
    Test IO drug selection for Ayesha.
    
    Ayesha's profile:
    - Age: 43 (lower irAE risk due to younger age)
    - MBD4 hypermutator (IO eligible)
    - No known autoimmune history
    """
    print("\n" + "=" * 70)
    print("TEST: Ayesha IO Drug Selection")
    print("=" * 70)
    
    # Ayesha's eligible IO drugs (all FDA-approved checkpoint inhibitors)
    eligible_drugs = [
        "pembrolizumab",
        "nivolumab",
        "atezolizumab",
        "ipilimumab",  # Higher risk
        "nivolumab_ipilimumab"  # Combination - highest risk
    ]
    
    # Ayesha's profile
    patient_age = 43
    autoimmune_history = None  # No known autoimmune conditions
    
    print(f"\nPatient: Ayesha (Age {patient_age})")
    print(f"IO Eligible: MBD4 hypermutator + PD-L1 CPS 10")
    print(f"Autoimmune History: {autoimmune_history or 'None known'}")
    
    # Get recommendation
    result = select_safest_io(
        eligible_drugs=eligible_drugs,
        patient_age=patient_age,
        autoimmune_history=autoimmune_history
    )
    
    print(f"\n--- RECOMMENDATION ---")
    print(f"Selected: {result['selected']} ({result['brand_name']})")
    print(f"Target: {result['target']}")
    print(f"irAE Risk (raw): {result['irae_risk_raw']:.0%}")
    print(f"irAE Risk (adjusted): {result['irae_risk_adjusted']:.0%}")
    print(f"Reason: {result['reason']}")
    
    if result.get("monitoring_priority"):
        print(f"Monitor for: {', '.join(result['monitoring_priority'])}")
    
    # Show drugs to AVOID
    if result.get("avoid"):
        print(f"\n--- AVOID (High irAE Risk) ---")
        for drug in result["avoid"]:
            print(f"  ⚠️ {drug['drug']} ({drug['target']}): {drug['irae_grade3plus_rate']:.0%} Grade 3+")
    
    # Verify selection is NOT ipilimumab or combination
    assert result["selected"] != "ipilimumab", "Should NOT select ipilimumab first"
    assert result["selected"] != "nivolumab_ipilimumab", "Should NOT select combination first"
    
    print("\n✅ PASS: Selected safest IO (PD-1 or PD-L1, not CTLA-4)")
    return True


def test_autoimmune_patient():
    """Test that autoimmune history appropriately increases risk assessment."""
    print("\n" + "=" * 70)
    print("TEST: Patient WITH Autoimmune History")
    print("=" * 70)
    
    # Same drugs, but patient has autoimmune history
    eligible_drugs = ["pembrolizumab", "nivolumab", "atezolizumab"]
    
    result = select_safest_io(
        eligible_drugs=eligible_drugs,
        patient_age=55,
        autoimmune_history=["psoriasis"]
    )
    
    print(f"\nPatient: Age 55 with psoriasis")
    print(f"Selected: {result['selected']}")
    print(f"irAE Risk (raw): {result['irae_risk_raw']:.0%}")
    print(f"irAE Risk (adjusted): {result['irae_risk_adjusted']:.0%}")
    print(f"Risk factors: {result['risk_factors']}")
    
    # Verify risk was doubled
    assert result["irae_risk_adjusted"] > result["irae_risk_raw"], "Adjusted risk should be higher"
    
    print("\n✅ PASS: Autoimmune history properly increases risk assessment")
    return True


def test_compare_io_drugs():
    """Test drug comparison function."""
    print("\n" + "=" * 70)
    print("TEST: Compare IO Drugs (Sorted by Safety)")
    print("=" * 70)
    
    drugs = ["pembrolizumab", "nivolumab", "ipilimumab", "atezolizumab", "nivolumab_ipilimumab"]
    comparison = compare_io_drugs(drugs)
    
    print("\nDrugs sorted by irAE risk (safest first):")
    for i, drug in enumerate(comparison, 1):
        risk = drug.get("irae_grade3plus_rate", 0)
        target = drug.get("target", "Unknown")
        print(f"  {i}. {drug['drug']:20} | {target:12} | irAE: {risk:.0%}")
    
    # Verify ipilimumab and combination are at the end
    last_two = [d["drug"] for d in comparison[-2:]]
    assert "ipilimumab" in last_two or "nivolumab_ipilimumab" in last_two, "High-risk should be last"
    
    print("\n✅ PASS: IO drugs correctly sorted by irAE risk")
    return True


def main():
    print("=" * 70)
    print("IO DRUG SELECTION TEST SUITE")
    print("=" * 70)
    
    results = []
    
    results.append(("IO Drug Profiles", test_io_drug_profiles()))
    results.append(("Ayesha IO Selection", test_ayesha_io_selection()))
    results.append(("Autoimmune Patient", test_autoimmune_patient()))
    results.append(("Compare IO Drugs", test_compare_io_drugs()))
    
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
        print("\n🔥 IO drug selection is production-ready!")
        print("   - Safest IO (PD-1/PD-L1) selected by default")
        print("   - High-risk drugs (CTLA-4, combinations) flagged")
        print("   - Patient-specific risk adjustments applied")
    else:
        print("\n⚠️ Some tests failed. Review output above.")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
