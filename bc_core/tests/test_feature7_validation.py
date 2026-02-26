"""
Feature 7 -- Data Validation + Anomaly Detection -- Smoke Tests.

Tests:
  1. Normal transaction -> no warnings
  2. Outlier detection -> warning when amount > 5x average
  3. Duplicate detection -> warning on same amount+type+day
  4. Future date -> warning
  5. Amount range -> warning on negative / over 1Cr
  6. POST /validation/check -> dry-run validation
  7. GET /validation/clients/<id>/anomalies -> anomaly summary
  8. Warnings array in create_transaction response
  9. Gap detection batch job
  10. Edge cases: 401, 403, 404
"""
import sys
import os
import io

# Fix Windows console unicode
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.config import Config


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS = {}
    RATELIMIT_ENABLED = False


from app import create_app
from core.extensions import db


def run_tests():
    app = create_app(config_class=TestConfig)

    passed = 0
    failed = 0

    def check(label, condition, detail=""):
        nonlocal passed, failed
        if condition:
            print(f"  PASS  {label}")
            passed += 1
        else:
            print(f"  FAIL  {label}  -- {detail}")
            failed += 1

    with app.app_context():
        db.create_all()
        client = app.test_client()

        # == SETUP ==
        print("\n=== SETUP ===")

        # Register CA
        r1 = client.post("/auth/register", json={
            "name": "CA Test",
            "email": "ca7@test.com",
            "password": "StrongPass123!",
            "phone": "9876543211",
            "firm_name": "Test & Co",
            "city": "Delhi",
            "state": "Delhi",
        })
        check("CA register", r1.status_code == 201, f"got {r1.status_code}")
        reg = r1.get_json()["data"]

        r2 = client.post("/auth/verify-otp", json={
            "user_id": reg["user_id"],
            "otp": reg["otp_dev_only"],
        })
        check("Verify OTP", r2.status_code == 200)
        ca_token = r2.get_json()["data"]["access_token"]
        ca_h = {"Authorization": f"Bearer {ca_token}"}

        # Create client business
        r3 = client.post("/clients", json={
            "name": "Shop Beta",
            "business_type": "retail",
            "state": "Delhi",
            "phone": "9111111111",
            "gstin": "07AAACW8900A1Z5",
            "expected_turnover": 1500000,
        }, headers=ca_h)
        check("Create client", r3.status_code == 201)
        biz_data = r3.get_json()["data"]
        biz_id = biz_data["client"]["id"] if "client" in biz_data else biz_data["id"]
        invite_code = biz_data.get("client", {}).get("invite_code") or biz_data.get("invite_code")

        # Accept invite as client (requires pin, then verify-otp)
        r_inv = client.post("/invite/accept", json={
            "invite_code": invite_code,
            "name": "Client Beta",
            "phone": "9111111111",
            "pin": "1234",
        })
        if r_inv.status_code in (200, 201):
            inv_data = r_inv.get_json()["data"]
            cl_user_id = inv_data["user_id"]
            cl_otp = inv_data.get("otp_dev_only")
            # Verify client OTP
            r_inv2 = client.post("/invite/verify-otp", json={
                "user_id": cl_user_id,
                "otp": cl_otp,
            })
            if r_inv2.status_code == 200:
                cl_token = r_inv2.get_json()["data"]["access_token"]
                cl_h = {"Authorization": f"Bearer {cl_token}"}
                check("Client invite accepted + verified", True)
            else:
                print(f"  WARN  Client verify failed ({r_inv2.status_code}), using CA")
                cl_h = ca_h
        else:
            print(f"  WARN  Invite accept failed ({r_inv.status_code}), using CA for all tests")
            cl_h = ca_h

        # == TEST 1: Normal transaction (no warnings) ==
        print("\n=== TEST 1: Normal Transaction ===")
        r4 = client.post("/transactions", json={
            "type": "sale",
            "amount": 5000,
            "category": "General",
        }, headers=cl_h)
        check("Create tx status", r4.status_code == 201, f"got {r4.status_code}")
        tx_data = r4.get_json()["data"]
        check("Has warnings array", "warnings" in tx_data)
        # First transaction may have zero warnings (no history for outlier)
        print(f"  Warnings: {tx_data.get('warnings', [])}")

        # Add a few more transactions to build history
        for amt in [4000, 6000, 5500, 4500, 5000]:
            client.post("/transactions", json={
                "type": "sale",
                "amount": amt,
                "category": "Daily",
            }, headers=cl_h)

        # == TEST 2: Outlier detection ==
        print("\n=== TEST 2: Outlier Detection ===")
        avg_amount = 5000  # roughly
        outlier_amount = avg_amount * 6  # > 5x

        r5 = client.post("/transactions", json={
            "type": "sale",
            "amount": outlier_amount,
        }, headers=cl_h)
        check("Outlier tx status", r5.status_code == 201)
        warns = r5.get_json()["data"].get("warnings", [])
        outlier_w = [w for w in warns if w["rule"] == "outlier_detection"]
        check("Outlier warning present", len(outlier_w) > 0, f"warnings={warns}")
        if outlier_w:
            check("Outlier has details", "details" in outlier_w[0])
            print(f"  Outlier msg: {outlier_w[0]['message']}")

        # == TEST 3: Duplicate detection ==
        print("\n=== TEST 3: Duplicate Detection ===")
        # Create a transaction, then create same amount+type+day
        client.post("/transactions", json={
            "type": "expense",
            "amount": 1234,
            "category": "Rent",
        }, headers=cl_h)

        r6 = client.post("/transactions", json={
            "type": "expense",
            "amount": 1234,
            "category": "Rent",
        }, headers=cl_h)
        check("Dup tx status", r6.status_code == 201)
        warns2 = r6.get_json()["data"].get("warnings", [])
        dup_w = [w for w in warns2 if w["rule"] == "duplicate_detection"]
        check("Duplicate warning present", len(dup_w) > 0, f"warnings={warns2}")
        if dup_w:
            print(f"  Dup msg: {dup_w[0]['message']}")

        # == TEST 4: Future date ==
        print("\n=== TEST 4: Future Date ===")
        r7 = client.post("/validation/check", json={
            "type": "sale",
            "amount": 1000,
            "transaction_date": "2099-01-01",
        }, headers=cl_h)
        check("Future date check status", r7.status_code == 200, f"got {r7.status_code}")
        fd_data = r7.get_json()["data"]
        fd_warns = fd_data.get("warnings", [])
        fd_w = [w for w in fd_warns if w["rule"] == "future_date"]
        check("Future date warning", len(fd_w) > 0, f"warnings={fd_warns}")
        check("valid=false for future date", fd_data.get("valid") == False)

        # == TEST 5: Amount range ==
        print("\n=== TEST 5: Amount Range ===")
        r8 = client.post("/validation/check", json={
            "type": "sale",
            "amount": -500,
        }, headers=cl_h)
        check("Negative amount status", r8.status_code == 200)
        neg_warns = r8.get_json()["data"].get("warnings", [])
        neg_w = [w for w in neg_warns if w["rule"] == "amount_range"]
        check("Negative amount warning", len(neg_w) > 0, f"warnings={neg_warns}")

        r9 = client.post("/validation/check", json={
            "type": "sale",
            "amount": 20000000,  # 2 crore
        }, headers=cl_h)
        check("Over 1Cr status", r9.status_code == 200)
        big_warns = r9.get_json()["data"].get("warnings", [])
        big_w = [w for w in big_warns if w["rule"] == "amount_range"]
        check("Over 1Cr warning", len(big_w) > 0, f"warnings={big_warns}")

        # Normal amount -> valid=true
        r10 = client.post("/validation/check", json={
            "type": "sale",
            "amount": 500,
        }, headers=cl_h)
        check("Normal amount valid=true", r10.get_json()["data"]["valid"] == True)

        # == TEST 6: Dry-run validation (POST /validation/check) ==
        print("\n=== TEST 6: Dry-Run Validation ===")
        r11 = client.post("/validation/check", json={
            "type": "expense",
            "amount": 3000,
        }, headers=cl_h)
        check("Dry-run status", r11.status_code == 200)
        check("Has warning_count", "warning_count" in r11.get_json()["data"])
        check("Has valid field", "valid" in r11.get_json()["data"])

        # Missing fields
        r11b = client.post("/validation/check", json={
            "amount": 100,
        }, headers=cl_h)
        check("Missing type -> 400", r11b.status_code == 400)

        r11c = client.post("/validation/check", json={
            "type": "sale",
        }, headers=cl_h)
        check("Missing amount -> 400", r11c.status_code == 400)

        # == TEST 7: Anomaly summary (CA endpoint) ==
        print("\n=== TEST 7: Anomaly Summary ===")
        r12 = client.get(f"/validation/clients/{biz_id}/anomalies", headers=ca_h)
        check("Anomaly summary status", r12.status_code == 200, f"got {r12.status_code}")
        anom = r12.get_json()["data"]
        check("Has gap_days", "gap_days" in anom)
        check("Has gap_status", "gap_status" in anom)
        check("Has outlier_count_30d", "outlier_count_30d" in anom)
        check("Has duplicate_count_30d", "duplicate_count_30d" in anom)
        check("Has flagged_transactions", "flagged_transactions" in anom)
        check("Has averages", "averages" in anom)
        check("Has client_name", anom.get("client_name") == "Shop Beta")
        print(f"  Gap: {anom['gap_days']} days ({anom['gap_status']})")
        print(f"  Outliers: {anom['outlier_count_30d']}, Dups: {anom['duplicate_count_30d']}")
        print(f"  Flagged txs: {len(anom['flagged_transactions'])}")

        # == TEST 8: Gap detection batch job ==
        print("\n=== TEST 8: Gap Detection Batch ===")
        from modules.validation.service import run_gap_detection
        # Currently all transactions are today, so no gap expected
        gap_count = run_gap_detection()
        check("Gap detection ran", gap_count == 0, f"alerts_created={gap_count}")

        # == TEST 9: Edge cases ==
        print("\n=== TEST 9: Edge Cases ===")

        # No auth
        r_noauth = client.get(f"/validation/clients/{biz_id}/anomalies")
        check("No auth -> 401", r_noauth.status_code == 401)

        # Bad business
        r_bad = client.get("/validation/clients/99999/anomalies", headers=ca_h)
        check("Bad business -> 404", r_bad.status_code == 404)

        # Client trying CA-only endpoint
        r_cl_anom = client.get(f"/validation/clients/{biz_id}/anomalies", headers=cl_h)
        check("Client -> anomalies -> 403", r_cl_anom.status_code == 403)

        # == SUMMARY ==
        print(f"\n{'='*50}")
        print(f"RESULTS: {passed} passed, {failed} failed")
        if failed == 0:
            print("ALL FEATURE 7 TESTS PASSED")
        else:
            print("SOME TESTS FAILED")
        print(f"{'='*50}\n")

    return failed


if __name__ == "__main__":
    sys.exit(run_tests())
