# CLAUDE.md
Goal: Evaluate BharatCompliance as a real Indian SaaS startup — not as a college project or demo.

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**BharatCompliance** is a WhatsApp-first financial compliance platform for India's micro-businesses (street vendors, gig workers, freelancers). CA firms use it to serve clients via WhatsApp message parsing, AI-powered OCR (Gemini Vision), and a real-time compliance scoring engine.

Deployed at: https://bharatcomplianceb.onrender.com

## Repository Structure

The repo has two distinct Flask applications:

- **`bc_core/`** — Active codebase. Modular, API-first Flask app with SQLAlchemy + Alembic, JWT auth, and full compliance engine. This is the one to work on.
- **`legacy_app/`** — Deprecated. Template-based Flask app with a custom ORM layer. Do not extend this.

## Development Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the development server (from repo root)
python bc_core/app.py

# Run production server
gunicorn bc_core.app:app

# Database migrations (run from bc_core/)
flask db migrate -m "description"
flask db upgrade

# Run all tests
pytest bc_core/tests/

# Run a single test file
pytest bc_core/tests/test_compliance_phase3.py

# Run a specific test
pytest bc_core/tests/test_compliance_phase3.py::TestClassName::test_method_name -v
```

## bc_core Architecture

**App factory pattern** in `bc_core/app.py` — creates Flask app, initializes extensions, registers blueprints.

**Extensions** (`bc_core/core/extensions.py`): SQLAlchemy (`db`), Flask-Migrate (`migrate`), Flask-JWT-Extended (`jwt`).

**Module structure** — each feature module under `bc_core/modules/` follows: `routes.py` → `service.py` → `models.py`

| Module | URL Prefix | Purpose |
|--------|-----------|---------|
| `auth/` | `/auth` | User registration, login, JWT issuance |
| `organizations/` | `/orgs` | CA firm management |
| `businesses/` | `/businesses` | Client business registration |
| `statements/` | `/statements` | Financial transaction records |
| `evidence/` | `/evidence` | Proof documents (receipts, invoices) |
| `ocr/` | — | Gemini Vision API OCR extraction |
| `whatsapp/` | `/whatsapp` | WhatsApp webhook integration |
| `compliance/` | `/compliance` | Rule engine, scoring, alerts (Phase 3) |

**Database:** SQLite in development (`bc_core/instance/`), migrations managed by Alembic in `bc_core/migrations/`.

**Authentication:** JWT tokens via Flask-JWT-Extended. Passwords hashed with bcrypt (`bc_core/core/security.py`).

## Key Implementation Notes

- **Phase 3 compliance engine** (`bc_core/modules/compliance/`) is the most complex part — it computes a 0-100 compliance score using 12 rules (GST thresholds at ₹20L/₹40L, FSSAI for food vendors, sector-specific checks, etc.).
- **WhatsApp integration** (`bc_core/modules/whatsapp/`) — webhook receiver routes are partially stubbed; phone-to-business mapping and permission checks are incomplete.
- **OCR flow**: Image evidence → `ocr/` service calls Gemini Vision API → structured transaction data extracted → written to `statements/`.
- Tests use SQLite in-memory databases and pytest fixtures defined within each test file (no shared `conftest.py`).

## Environment Setup

Requires a `.env` file in `bc_core/` with at minimum:
- `SECRET_KEY` — Flask secret key
- `JWT_SECRET_KEY` — JWT signing key
- `GOOGLE_API_KEY` or equivalent — for Gemini Vision OCR
- `DATABASE_URL` — defaults to SQLite if not set
