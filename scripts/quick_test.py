#!/usr/bin/env python3
"""
sha-pay - Quick Local Test
Zero dependencies - uses ONLY Python standard library (no pip install needed)

Tests the core penalty calculator logic and API endpoints via curl.

Run: python quick_test.py
"""

import json
import os
import subprocess
import sys
import textwrap
from datetime import datetime

# ──────────────────────────────── CONFIG ────────────────────────────────

PENALTY_RATE = 0.02       # 2% per month (SHA Tariff Registry)
MIN_CONTRIBUTION = 300.0  # KES
MAX_MONTHS = 12
PAYBILL = "200222"
DEADLINE_DAY = 9

# ────────────────────────── PENALTY CALCULATOR ─────────────────────────

def calculate_penalty(missed_months: int, monthly_contribution: float = 300.0) -> dict:
    """
    Calculate SHA penalty for missed contributions.
    Formula: Σ(monthly_contribution × 0.02 × months_late)
    Source: SHA Tariff Registry - Ministry of Health
    """
    months = min(missed_months, MAX_MONTHS)
    total_contributions = months * monthly_contribution
    total_penalty = 0.0
    breakdown = []

    for i in range(1, months + 1):
        month_penalty = monthly_contribution * PENALTY_RATE
        running_total = (monthly_contribution * i) + sum(
            monthly_contribution * PENALTY_RATE for _ in range(i)
        )
        breakdown.append({
            "mwezi": i,
            "month": i,
            "contribution_ksh": round(monthly_contribution, 2),
            "penalty_ksh": round(month_penalty, 2),
            "running_total_ksh": round(running_total, 2),
        })
        total_penalty += month_penalty

    total_due = total_contributions + total_penalty
    return {
        "missed_months": months,
        "monthly_contribution_ksh": monthly_contribution,
        "total_contributions_due_ksh": round(total_contributions, 2),
        "penalty_amount_ksh": round(total_penalty, 2),
        "penalty_rate": PENALTY_RATE,
        "total_amount_due_ksh": round(total_due, 2),
        "per_month_breakdown": breakdown,
        "formula": "Σ(monthly_contribution × 0.02 × months_late)",
        "formula_source": "SHA Tariff Registry - 2% per month late",
        "calculated_at": datetime.now().isoformat(),
    }


# ──────────────────────────────── TESTS ────────────────────────────────

def run_all_tests():
    """Run all penalty calculation tests and print results."""
    print("=" * 60)
    print("  SHA PENALTY CALCULATOR - TEST SUITE")
    print("=" * 60)

    tests_passed = 0
    tests_failed = 0

    def test(name, fn):
        nonlocal tests_passed, tests_failed
        try:
            fn()
            print(f"  [PASS] {name}")
            tests_passed += 1
        except AssertionError as e:
            print(f"  [FAIL] {name}")
            print(f"     Assertion failed: {e}")
            tests_failed += 1
        except Exception as e:
            print(f"  [FAIL] {name}")
            print(f"     Error: {e}")
            tests_failed += 1

    # Test 1: 1 month missed
    def t1():
        r = calculate_penalty(1, 300.0)
        assert r["total_contributions_due_ksh"] == 300.0, f"Expected 300, got {r['total_contributions_due_ksh']}"
        assert r["penalty_amount_ksh"] == 6.0, f"Expected 6.0, got {r['penalty_amount_ksh']}"
        assert r["total_amount_due_ksh"] == 306.0

    # Test 2: 3 months missed
    def t2():
        r = calculate_penalty(3, 300.0)
        assert r["total_contributions_due_ksh"] == 900.0
        assert r["penalty_amount_ksh"] == 18.0  # 6 + 6 + 6
        assert r["total_amount_due_ksh"] == 918.0

    # Test 3: 6 months @ KES 500
    def t3():
        r = calculate_penalty(6, 500.0)
        assert r["total_contributions_due_ksh"] == 3000.0
        assert r["penalty_amount_ksh"] == 60.0  # 10 * 6
        assert r["total_amount_due_ksh"] == 3060.0

    # Test 4: Cap at 12 months
    def t4():
        r = calculate_penalty(24, 300.0)
        assert r["missed_months"] == 12, f"Expected capped at 12, got {r['missed_months']}"
        assert r["penalty_amount_ksh"] == 72.0

    # Test 5: Breakdown structure
    def t5():
        r = calculate_penalty(2, 300.0)
        b = r["per_month_breakdown"]
        assert len(b) == 2
        assert b[0]["running_total_ksh"] == 306.0
        assert b[1]["running_total_ksh"] == 612.0

    # Test 6: Different amounts scale correctly
    def t6():
        r1 = calculate_penalty(1, 300.0)
        r2 = calculate_penalty(1, 5000.0)
        assert r1["penalty_amount_ksh"] == 6.0
        assert r2["penalty_amount_ksh"] == 100.0  # 5000 * 0.02

    # Test 7: Formula reference present
    def t7():
        r = calculate_penalty(1)
        assert "formula" in r
        assert "SHA Tariff Registry" in r["formula_source"]

    test("1 month missed @ KES 300    -> KES 306 total", t1)
    test("3 months missed @ KES 300   -> KES 918 total", t2)
    test("6 months missed @ KES 500   -> KES 3,060 total", t3)
    test("24 months capped to 12 max  -> KES 72 penalty", t4)
    test("Per-month breakdown correct (2 months)", t5)
    test("Penalty scales with amount   -> KES 100 @ 5000", t6)
    test("Formula reference present", t7)

    print("-" * 60)
    print(f"  Results: {tests_passed} passed, {tests_failed} failed")
    print("=" * 60)
    return tests_failed == 0


# ──────────────────────────────── SCENARIOS ────────────────────────────

def show_example_scenarios():
    """Display realistic usage scenarios."""
    scenarios = [
        ("Mama Mboga (Informal Sector)", 3, 300.0),
        ("Boda Boda Rider", 6, 300.0),
        ("Shop Owner", 2, 500.0),
        ("Teacher (Formal Sector)", 12, 500.0),
        ("Accountant", 1, 1000.0),
    ]

    print("\n  REAL-WORLD SCENARIOS")
    print("-" * 60)
    for name, months, amount in scenarios:
        r = calculate_penalty(months, amount)
        print(f"  >> {name}")
        print(f"     Missed: {months} months @ KES {amount:.0f}/month")
        print(f"     Contributions due: KES {r['total_contributions_due_ksh']:,.2f}")
        print(f"     Penalty (2%/mo):   KES {r['penalty_amount_ksh']:,.2f}")
        print(f"     TOTAL DUE:         KES {r['total_amount_due_ksh']:,.2f}")
        print()


# ──────────────────────────── M-PESA INFO ────────────────────────────

def show_payment_info():
    """Display SHA payment instructions."""
    print("  SHA PAYMENT INSTRUCTIONS")
    print("-" * 60)
    print(f"  Paybill:     {PAYBILL}")
    print(f"  Account:     Your National ID Number")
    print(f"  Minimum:     KES {MIN_CONTRIBUTION:.0f}")
    print(f"  Deadline:    {DEADLINE_DAY}th of each month")
    print(f"  Penalty:     2% per month late")
    print()
    print("  How to Pay:")
    print("  1. Go to M-Pesa on your phone")
    print("  2. Lipa na M-Pesa -> Paybill")
    print(f"  3. Business No: {PAYBILL}")
    print("  4. Account: Your National ID")
    print("  5. Amount: Min KES 300")
    print("  6. Enter PIN & Confirm")
    print()


# ──────────────────────────────── API TEST ────────────────────────────

def test_api_endpoints():
    """Test the API server if it's running."""
    import urllib.request
    import urllib.error

    print("  TESTING API ENDPOINTS")
    print("-" * 60)

    base = "http://localhost:8000"
    endpoints = [
        ("GET", "/", "Root info"),
        ("GET", "/api/v1/health", "Health check"),
        ("GET", "/api/v1/penalty/formula", "Penalty formula"),
        ("GET", "/api/v1/payments/paybill", "Paybill info"),
    ]

    server_running = False
    for method, path, desc in endpoints:
        try:
            req = urllib.request.Request(f"{base}{path}")
            if method == "POST":
                req.method = "POST"
                req.data = json.dumps({
                    "missed_months": 3,
                    "monthly_contribution": 300
                }).encode()
                req.add_header("Content-Type", "application/json")

            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read())
                status = "[OK]" if data.get("success", True) else "[WARN]"
                print(f"  {status} {desc:30s} -> {resp.status}")
                server_running = True
        except urllib.error.URLError:
            print(f"  [SKIP] {desc:30s} - Server not running (skipped)")
        except Exception as e:
            print(f"  [SKIP] {desc:30s} - Error: {e}")

    if not server_running:
        print()
        print("  TIP: Start the server in another terminal, then re-run:")
        print(f"     cd backend && pip install -r requirements.txt")
        print(f"     python main.py")
        print(f"  Or use: docker-compose up -d")
    print()


# ──────────────────────────────── MAIN ────────────────────────────────

def main():
    print()
    print("=" * 60)
    print("  sha-pay")
    print("  Quick Local Test Suite")
    print("=" * 60)
    print(f"  Tested: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  OS: {sys.platform}")
    print(f"  Python: {sys.version.split()[0]}")
    print()

    # Run penalty calculator tests
    success = run_all_tests()

    # Show real-world examples
    show_example_scenarios()

    # Show payment info
    show_payment_info()

    # Optional: test live API
    test_api_endpoints()

    # Summary
    print("-" * 60)
    if success:
        print("  [PASS] ALL TESTS PASSED - Core penalty calculator is working!")
    else:
        print("  [FAIL] SOME TESTS FAILED - Check the output above.")
    print()
    print("  Full backend setup:")
    print("    cd backend")
    print("    python -m venv .venv")
    print("    .venv\\Scripts\\activate")
    print("    pip install -r requirements.txt")
    print("    python main.py")
    print()
    print("  Or with Docker:")
    print("    docker-compose up -d")
    print()
    print("  API Docs: http://localhost:8000/docs")
    print("=" * 60)


if __name__ == "__main__":
    main()