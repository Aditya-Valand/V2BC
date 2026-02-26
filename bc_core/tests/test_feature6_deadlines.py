"""
Feature 6 — Compliance Calendar + Deadline Management — Smoke Tests.

Tests:
  1. Generate deadlines for a GST-registered client
  2. GET /deadlines/clients/<id> — view all deadlines
  3. GET /deadlines/upcoming — CA view upcoming deadlines
  4. POST /deadlines/<id>/complete — CA marks deadline completed
  5. POST /deadlines/<id>/acknowledge — Client acknowledges reminder
  6. POST /reminders/send-bulk — bulk deadline reminders
  7. POST /deadlines/generate/<id> — idempotent re-generation
  8. Edge cases: 401, 403, 404, bad status, already completed
"""
import sys
import os

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

        # ── Setup: register CA (register -> verify-otp) ────── #
        print("\n=== SETUP ===")

        # 1. Register CA
        r1 = client.post("/auth/register", json={
            "name": "CA Sharma",
            "email": "ca@test.com",
            "password": "StrongPass123!",
            "phone": "9876543210",
            "firm_name": "Sharma & Associates",
            "city": "Mumbai",
            "state": "Maharashtra",
        })
        check("CA register", r1.status_code == 201, f"got {r1.status_code} body={r1.get_json()}")
        reg_data = r1.get_json()["data"]
        ca_user_id = reg_data["user_id"]
        otp = reg_data.get("otp_dev_only")

        # 2. Verify OTP
        r2 = client.post("/auth/verify-otp", json={
            "user_id": ca_user_id,
            "otp": otp,
        })
        check("Verify OTP", r2.status_code == 200, f"got {r2.status_code} body={r2.get_json()}")
        ca_token = r2.get_json()["data"]["access_token"]
        ca_headers = {"Authorization": f"Bearer {ca_token}"}

        # 3. Create client business (with GSTIN for GST deadlines, food sector for FSSAI)
        r3 = client.post("/clients", json={
            "name": "Biz Alpha",
            "business_type": "food",
            "state": "Maharashtra",
            "phone": "9123456789",
            "gstin": "27AAPFU0939F1ZV",
            "expected_turnover": 2500000,
        }, headers=ca_headers)
        check("Create client", r3.status_code == 201, f"got {r3.status_code} body={r3.get_json()}")
        biz_data = r3.get_json()["data"]
        biz_id = biz_data["client"]["id"] if "client" in biz_data else biz_data["id"]
        print(f"  Business ID: {biz_id}")

        # ── Test 1: Generate deadlines ──────────────────────── #
        print("\n=== TEST 1: Generate Deadlines ===")
        r4 = client.post(f"/deadlines/generate/{biz_id}", headers=ca_headers)
        check("Generate deadlines status", r4.status_code in (200, 201), f"got {r4.status_code} body={r4.get_json()}")
        gen_data = r4.get_json()["data"]
        check("Deadlines created > 0", gen_data["deadlines_created"] > 0,
              f"created={gen_data['deadlines_created']}")
        print(f"  Deadlines created: {gen_data['deadlines_created']}")

        # ── Test 2: Idempotent re-generation ─────────────────── #
        print("\n=== TEST 2: Idempotent Re-generation ===")
        r4b = client.post(f"/deadlines/generate/{biz_id}", headers=ca_headers)
        check("Re-generate status", r4b.status_code == 200, f"got {r4b.status_code}")
        gen2 = r4b.get_json()["data"]
        check("No new deadlines on re-run", gen2["deadlines_created"] == 0,
              f"created={gen2['deadlines_created']}")

        # ── Test 3: GET client deadlines ────────────────────── #
        print("\n=== TEST 3: GET Client Deadlines ===")
        r5 = client.get(f"/deadlines/clients/{biz_id}", headers=ca_headers)
        check("Get deadlines status", r5.status_code == 200, f"got {r5.status_code}")
        dl_data = r5.get_json()["data"]
        deadlines = dl_data["deadlines"]
        check("Has deadlines list", len(deadlines) > 0, f"count={len(deadlines)}")
        check("Has summary", "summary" in dl_data)
        check("Summary has pending count", dl_data["summary"]["pending"] > 0)
        print(f"  Total deadlines: {dl_data['summary']['total']}")
        print(f"  Pending: {dl_data['summary']['pending']}")

        # Check deadline types
        types = set(d["deadline_type"] for d in deadlines)
        print(f"  Types: {types}")
        check("Has GSTR-3B deadlines", "gstr3b" in types, f"types={types}")

        # Filter by status
        r5b = client.get(f"/deadlines/clients/{biz_id}?status=pending", headers=ca_headers)
        check("Filter by status=pending", r5b.status_code == 200)

        # ── Test 4: GET upcoming deadlines (CA view) ────────── #
        print("\n=== TEST 4: GET Upcoming Deadlines ===")
        r6 = client.get("/deadlines/upcoming", headers=ca_headers)
        check("Upcoming deadlines status", r6.status_code == 200, f"got {r6.status_code}")
        up_data = r6.get_json()["data"]
        check("Has period info", "period" in up_data)
        check("Has summary", "summary" in up_data)
        check("Has this_week list", "this_week" in up_data)
        check("Has overdue list", "overdue" in up_data)
        print(f"  Total upcoming (30d): {up_data['summary']['total_upcoming']}")
        print(f"  This week: {up_data['summary']['this_week']}")
        print(f"  Overdue: {up_data['summary']['overdue']}")

        # With custom days param
        r6b = client.get("/deadlines/upcoming?days=7", headers=ca_headers)
        check("Upcoming 7 days", r6b.status_code == 200)

        # ── Test 5: Complete a deadline ─────────────────────── #
        print("\n=== TEST 5: Complete Deadline ===")
        first_dl = deadlines[0]
        dl_id = first_dl["id"]

        r7 = client.post(f"/deadlines/{dl_id}/complete", json={
            "notes": "Filed on time via portal."
        }, headers=ca_headers)
        check("Complete deadline status", r7.status_code == 200, f"got {r7.status_code} body={r7.get_json()}")
        comp_data = r7.get_json()["data"]
        check("Status is completed", comp_data["status"] == "completed")
        check("Has completed_at", comp_data["completed_at"] is not None)
        check("Has notes", comp_data["notes"] == "Filed on time via portal.")

        # Try completing again -> 400
        r7b = client.post(f"/deadlines/{dl_id}/complete", headers=ca_headers)
        check("Double complete -> 400", r7b.status_code == 400, f"got {r7b.status_code}")

        # ── Test 6: Acknowledge deadline ────────────────────── #
        print("\n=== TEST 6: Acknowledge Deadline ===")
        if len(deadlines) > 1:
            dl2_id = deadlines[1]["id"]
            r8 = client.post(f"/deadlines/{dl2_id}/acknowledge", headers=ca_headers)
            check("Acknowledge deadline", r8.status_code == 200, f"got {r8.status_code}")
            ack_data = r8.get_json()["data"]
            check("Status is acknowledged", ack_data["status"] == "acknowledged")
            check("Has acknowledged_at", ack_data["acknowledged_at"] is not None)
        else:
            print("  SKIP — only 1 deadline available")

        # ── Test 7: Send bulk reminders ─────────────────────── #
        print("\n=== TEST 7: Send Bulk Reminders ===")
        r9 = client.post("/reminders/send-bulk", json={
            "client_ids": [biz_id],
            "message": "Please review your upcoming filings.",
            "deadline_type": "gstr3b",
        }, headers=ca_headers)
        check("Send-bulk status", r9.status_code == 200, f"got {r9.status_code} body={r9.get_json()}")
        bulk_data = r9.get_json()["data"]
        check("Has total", "total" in bulk_data)
        check("Has details", "details" in bulk_data)
        print(f"  Sent: {bulk_data.get('sent')}, Skipped: {bulk_data.get('skipped')}")

        # send-bulk with "all"
        r9b = client.post("/reminders/send-bulk", json={
            "client_ids": "all",
            "message": "General compliance reminder.",
        }, headers=ca_headers)
        check("Send-bulk all", r9b.status_code == 200, f"got {r9b.status_code}")

        # ── Test 8: Edge cases ──────────────────────────────── #
        print("\n=== TEST 8: Edge Cases ===")

        # No auth
        r_noauth = client.get(f"/deadlines/clients/{biz_id}")
        check("No auth -> 401", r_noauth.status_code == 401, f"got {r_noauth.status_code}")

        # Generate for non-existent business
        r_bad_gen = client.post("/deadlines/generate/99999", headers=ca_headers)
        check("Bad business -> 404", r_bad_gen.status_code == 404, f"got {r_bad_gen.status_code}")

        # Complete non-existent deadline
        r_bad_comp = client.post("/deadlines/99999/complete", headers=ca_headers)
        check("Bad deadline -> 400", r_bad_comp.status_code == 400, f"got {r_bad_comp.status_code}")

        # Send-bulk empty message
        r_bad_bulk = client.post("/reminders/send-bulk", json={
            "client_ids": [biz_id],
            "message": "",
        }, headers=ca_headers)
        check("Empty message -> 400", r_bad_bulk.status_code == 400, f"got {r_bad_bulk.status_code}")

        # Send-bulk no client_ids
        r_bad_bulk2 = client.post("/reminders/send-bulk", json={
            "message": "Hello",
        }, headers=ca_headers)
        check("No client_ids -> 400", r_bad_bulk2.status_code == 400, f"got {r_bad_bulk2.status_code}")

        # ── Test 9: FSSAI deadline for food sector ──────────── #
        print("\n=== TEST 9: FSSAI Deadline (food sector) ===")
        fssai = [d for d in deadlines if d["deadline_type"] == "fssai_renewal"]
        check("Has FSSAI deadline (food sector)", len(fssai) > 0,
              f"found={len(fssai)}, types={types}")

        # ── Test 10: Deadline detail fields ─────────────────── #
        print("\n=== TEST 10: Deadline Detail Fields ===")
        sample = deadlines[0]
        check("Has id", "id" in sample)
        check("Has deadline_type", "deadline_type" in sample)
        check("Has due_date", "due_date" in sample and sample["due_date"] is not None)
        check("Has description", "description" in sample and sample["description"] is not None)
        check("Has status", "status" in sample)
        check("Has period_start", "period_start" in sample)

        # ── Summary ─────────────────────────────────────────── #
        print(f"\n{'='*50}")
        print(f"RESULTS: {passed} passed, {failed} failed")
        if failed == 0:
            print("ALL FEATURE 6 TESTS PASSED")
        else:
            print("SOME TESTS FAILED")
        print(f"{'='*50}\n")

    return failed


if __name__ == "__main__":
    sys.exit(run_tests())
