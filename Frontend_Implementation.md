# BharatCompliance — Frontend Implementation Guide

> Complete API reference, auth flows, data structures, and UI patterns for building the frontend.

**Base URL (Production):** `https://bharatcomplianceb.onrender.com`
**Base URL (Dev):** `http://localhost:5000`

---

## Table of Contents

1. [Response Envelope](#1-response-envelope)
2. [Authentication & JWT](#2-authentication--jwt)
3. [Auth Endpoints](#3-auth-endpoints)
4. [Client Management](#4-client-management-clients--invite)
5. [Transactions](#5-transactions-transactions--my)
6. [Evidence / OCR](#6-evidence--ocr-evidence)
7. [Dashboard](#7-dashboard-dashboard)
8. [Compliance Engine](#8-compliance-engine-compliance)
9. [Reminders](#9-reminders-reminders)
10. [Deadlines / Calendar](#10-deadlines--calendar-deadlines)
11. [Validation / Anomaly](#11-validation--anomaly-detection-validation)
12. [WhatsApp](#12-whatsapp-whatsapp)
13. [Rate Limits](#13-rate-limit-reference)
14. [Error Codes](#14-global-error-codes)
15. [Recommended UI Flows](#15-recommended-ui-flows)

---

## 1. Response Envelope

Every endpoint returns this consistent JSON shape:

```json
// Success
{ "success": true,  "data": { ... }, "error": null }

// Error
{ "success": false, "data": null,  "error": "message" | { field_errors } }
```

**Exception:** Compliance module (`/compliance/*`) returns raw JSON without the envelope.

---

## 2. Authentication & JWT

### Token Setup

| Item | Value |
|------|-------|
| Header | `Authorization: Bearer <access_token>` |
| Access token TTL | **1 hour** |
| Refresh token TTL | **30 days** |
| Token type | JWT (Flask-JWT-Extended) |

### JWT Claims (decoded payload)

**CA user token:**
```json
{
  "sub": "42",           // user_id (string)
  "role": "ca_owner",   // "ca_owner" | "ca_staff"
  "org_id": 7,
  "jti": "uuid-for-blocklist"
}
```

**Client user token:**
```json
{
  "sub": "88",
  "role": "client",
  "org_id": 7,
  "business_id": 15     // client's linked business
}
```

### Roles & Permissions

| Role | Description | Can Access |
|------|-------------|------------|
| `ca_owner` | CA firm owner | Dashboard, all clients, compliance, deadlines, reminders |
| `ca_staff` | CA staff member | Same as ca_owner (within same org) |
| `client` | Business owner | Own transactions, own summary, own deadlines, validation/check |

### JWT Error Codes

All return HTTP 401:

| Code | Meaning | Frontend Action |
|------|---------|-----------------|
| `TOKEN_EXPIRED` | Token expired | Call `/auth/refresh` |
| `TOKEN_INVALID` | Malformed token | Redirect to login |
| `TOKEN_MISSING` | No Authorization header | Redirect to login |
| `TOKEN_REVOKED` | Logged out / blocklisted | Redirect to login |

### Token Refresh Flow

```
1. API returns 401 with code: "TOKEN_EXPIRED"
2. Call POST /auth/refresh with refresh_token in Authorization header
3. Get new access_token
4. Retry original request
5. If refresh also fails → redirect to login
```

---

## 3. Auth Endpoints

### `POST /auth/register`

Register a new CA user + auto-create organization.

**Request:**
```json
{
  "name": "Priya Nair",              // required, 2-120 chars
  "email": "priya@ca.in",            // required, valid email
  "password": "Secret123",           // required, >=8 chars, must have 1 digit
  "firm_name": "Nair & Associates",  // required, 2-150 chars
  "city": "Kochi",                   // required
  "state": "Kerala",                 // required
  "phone": "9876543210",             // optional, 10-digit Indian mobile
  "license_number": "MRN12345"       // optional
}
```

**Response (201):**
```json
{
  "data": {
    "user_id": 42,
    "message": "Account created! We've sent a 6-digit verification code to priya@ca.in.",
    "otp_dev_only": "381920"   // DEV ONLY — not in production
  }
}
```

**Errors:** 400 (validation), 409 (email/phone already exists)

**Frontend:** After success, navigate to OTP verification screen with `user_id`.

---

### `POST /auth/verify-otp`

Verify email OTP after registration.

**Request:**
```json
{ "user_id": 42, "otp": "381920" }
```

**Response (200):**
```json
{
  "data": {
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "token_type": "Bearer",
    "user": {
      "id": 42, "name": "Priya Nair", "email": "priya@ca.in",
      "phone": "9876543210", "role": "ca_owner",
      "is_verified": true, "last_login": "2026-02-27T10:00:00"
    },
    "org": {
      "id": 7, "name": "Nair & Associates",
      "city": "Kochi", "state": "Kerala",
      "plan": "free", "client_count": 0
    }
  }
}
```

**OTP rules:** Expires in 10 min, max 5 wrong attempts.

**Frontend:** Store both tokens, navigate to dashboard.

---

### `POST /auth/resend-otp`

**Request:** `{ "user_id": 42 }`

**Response (200):**
```json
{ "data": { "user_id": 42, "message": "A new OTP has been sent.", "otp_dev_only": "..." } }
```

**Errors:** 400 (already verified), 429 (60-second cooldown)

**Frontend:** Show 60-second countdown timer before allowing resend.

---

### `POST /auth/login`

CA users only (clients use invite flow).

**Request:**
```json
{ "email": "priya@ca.in", "password": "Secret123" }
```

**Response (200):** Same as verify-otp — includes `access_token`, `refresh_token`, `user`, `org`.

**Errors:** 401 (wrong credentials), 403 (email not verified — redirect to OTP screen)

---

### `POST /auth/refresh`

**Header:** `Authorization: Bearer <refresh_token>` (NOT access token)

**Response (200):**
```json
{ "data": { "access_token": "eyJ...", "token_type": "Bearer" } }
```

---

### `GET /auth/me`

Get current user profile.

**Response (200):**
```json
{
  "data": {
    "user": { "id": 42, "name": "...", "email": "...", "role": "ca_owner", ... },
    "org": { "id": 7, "name": "...", "plan": "free", ... },
    "org_role": "ca_owner"
  }
}
```

---

### `POST /auth/logout`

Call with access token to invalidate it. Call again with refresh token to fully log out.

**Response (200):**
```json
{ "data": { "message": "Successfully logged out." } }
```

---

## 4. Client Management (`/clients` + `/invite`)

### `POST /clients` — Add a new client

**Auth:** CA role required

**Request:**
```json
{
  "name": "Ram Prasad Tea Stall",     // required
  "business_type": "food",             // optional
  "state": "Maharashtra",             // optional
  "gstin": "27AAAAA0000A1Z5",         // optional (GSTIN regex validated)
  "pan": "AAAAA0000A",                // optional (PAN regex validated)
  "expected_turnover": 500000.0,       // optional (INR)
  "phone": "9876543210",              // optional
  "whatsapp_phone": "9876543210"       // optional
}
```

**Response (201):**
```json
{
  "data": {
    "client": {
      "id": 15, "name": "Ram Prasad Tea Stall",
      "business_type": "food", "state": "Maharashtra",
      "phone": "9876543210", "invite_code": "xK3mP9",
      "invite_status": "pending",
      "invite_expires_at": "2026-03-29T09:00:00",
      "is_active": true
    },
    "invite_url": "http://localhost:5173/invite/xK3mP9",
    "qr_svg": "<svg>...</svg>"
  }
}
```

**Frontend:** Show the QR code SVG and invite URL. CA shares this with the client.

---

### `GET /clients` — List all clients

**Auth:** CA role

**Response:**
```json
{
  "data": {
    "clients": [
      {
        "id": 15, "name": "Ram Prasad Tea Stall",
        "business_type": "food", "state": "Maharashtra",
        "phone": "9876543210", "invite_status": "active",
        "is_active": true,
        "statement_count": 23,
        "last_activity": "2026-02-25T14:30:00",
        "compliance_score": 72.5
      }
    ],
    "total": 1
  }
}
```

---

### `GET /clients/<id>` — Client details

**Response:** Full `ClientDetailSchema` with all fields including `invite_code`, `owner_name`, `owner_phone`.

---

### `PUT /clients/<id>` — Update client

**Request:** Any subset of create fields + `is_active: bool`

---

### `GET /clients/<id>/detail` — Rich client detail (CA view)

**Response:**
```json
{
  "data": {
    "client": { "id": 15, "name": "...", ... },
    "stats": {
      "total_sales_this_month": 45000.00,
      "total_expenses_this_month": 12000.00,
      "net_income_this_month": 33000.00,
      "transaction_count": 18,
      "with_evidence": 12, "without_evidence": 6,
      "evidence_breakdown": { "strong": 8, "medium": 3, "weak": 1 }
    },
    "compliance_color": "green",      // "red" | "yellow" | "green"
    "compliance_score": 72.5,
    "days_since_last_entry": 1,
    "recent_transactions": [ ... ]
  }
}
```

**Color logic:** green = entry in last 2 days, yellow = 3-4 days, red = 5+ days.

---

### `GET /clients/<id>/filing-summary` — Monthly filing data

**Query:** `?month=2026-02`

**Response:**
```json
{
  "data": {
    "client": { "id": 15, "name": "...", "gstin": "...", "business_type": "food" },
    "period": "2026-02",
    "totals": { "sales": 45000, "expenses": 12000, "net": 33000, "estimated_tax": 0 },
    "confidence_breakdown": { "high": 12, "medium": 4, "low": 2, "total": 18, "with_evidence": 12 },
    "transactions": [ ... ],
    "low_confidence_transactions": [ ... ]
  }
}
```

---

### `GET /clients/<id>/filing-summary/export` — Download Excel

Returns `.xlsx` file with 3 sheets: Summary, All Transactions, Low Confidence.

---

### `POST /clients/<id>/regenerate-invite`

Generates new invite code (old one becomes invalid).

**Response:** `{ "data": { "invite_url": "...", "qr_svg": "...", "invite_code": "..." } }`

---

### Client Invite Flow (Public — No Auth)

#### `GET /invite/<invite_code>` — Preview invite

```json
{
  "data": {
    "invite": {
      "invite_code": "xK3mP9",
      "ca_firm_name": "Nair & Associates",
      "client_name": "Ram Prasad Tea Stall",
      "invite_status": "pending",
      "is_expired": false
    }
  }
}
```

#### `POST /invite/accept` — Client accepts invite

```json
{
  "invite_code": "xK3mP9",    // required
  "name": "Ram Prasad",        // required
  "phone": "9123456789",       // required, 10-digit
  "pin": "1234"                // required, 4-6 digits (used as password)
}
```

**Response (201):**
```json
{ "data": { "user_id": 88, "message": "Invite accepted! OTP sent.", "otp_dev_only": "..." } }
```

**Errors:** 404 (bad code), 409 (already accepted/duplicate phone), 410 (expired)

#### `POST /invite/verify-otp` — Client verifies

```json
{ "user_id": 88, "otp": "592847" }
```

**Response (200):**
```json
{
  "data": {
    "access_token": "...", "refresh_token": "...",
    "user": { "id": 88, "name": "Ram Prasad", "role": "client" },
    "business": { "id": 15, "name": "Ram Prasad Tea Stall", "invite_status": "active" }
  }
}
```

**Frontend flow:** Invite link → show CA firm name → accept form → OTP → client dashboard.

---

## 5. Transactions (`/transactions` + `/my`)

### `POST /transactions` — Create transaction

**Auth:** Client role only (`business_id` from JWT)

**JSON body:**
```json
{
  "type": "sale",                    // required: "sale" | "expense"
  "amount": 2500.0,                 // required, >0
  "category": "food_sales",         // optional
  "transaction_date": "2026-02-27", // optional (default: today)
  "description": "Chai and snacks"  // optional
}
```

**Multipart (with photo):** Same fields as form data + `evidence_file` (image file, max 10MB).

**Response (201):**
```json
{
  "data": {
    "transaction": {
      "id": 101, "type": "sale", "amount": 2500.0,
      "category": "food_sales", "description": "Chai and snacks",
      "transaction_date": "2026-02-27",
      "confidence_level": "high",
      "source": "client_app",
      "evidence_id": 55
    },
    "duplicate_warning": null,
    "ocr_result": null,
    "quality_warning": null,
    "warnings": []
  }
}
```

### Important Response Fields

| Field | When Present | Frontend Action |
|-------|-------------|-----------------|
| `duplicate_warning` | Same amount+type in last 5 min | Show "You already entered this" toast |
| `ocr_result.conflict=true` | OCR amount differs >5% from entered | Show conflict dialog with both amounts |
| `quality_warning` | Photo is blurry (score < 40) | Show "Retake photo" suggestion |
| `warnings[]` | Validation anomalies detected | Show warning badges on transaction |

### Warning Object Shape (from `warnings[]`):
```json
{
  "rule": "outlier_detection",       // rule identifier
  "message": "Amount is 6x your 30-day average",
  "severity": "medium",             // "low" | "medium" | "high"
  "details": { "average": 5000, "ratio": 6.0 }
}
```

**Possible `rule` values:** `amount_range`, `future_date`, `outlier_detection`, `duplicate_detection`

---

### `PATCH /transactions/<id>` — Confirm amount (OCR conflict)

Called when user resolves an OCR conflict.

**Request:** `{ "amount": 2700.0 }`

**Response:** `{ "data": { "transaction": { "id": 101, "amount": 2700.0, "confidence_level": "high" } } }`

---

### `GET /my/transactions` — Client's transaction history

**Query params:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `type` | string | — | `"sale"` or `"expense"` |
| `from` | YYYY-MM-DD | — | Start date |
| `to` | YYYY-MM-DD | — | End date |
| `page` | int | 1 | Page number |
| `per_page` | int | 20 | Items per page (max 100) |

**Response:**
```json
{
  "data": {
    "transactions": [
      {
        "id": 101, "type": "sale", "amount": 2500.0,
        "category": "food_sales", "description": null,
        "transaction_date": "2026-02-27",
        "source": "client_app", "confidence_level": "high",
        "verified": false, "created_at": "...",
        "evidence_id": 55, "evidence_status": "success"
      }
    ],
    "total": 45, "page": 1, "per_page": 20, "pages": 3
  }
}
```

---

### `GET /my/summary` — Monthly summary

**Query:** `?month=2026-02`

**Response:**
```json
{
  "data": {
    "summary": {
      "month": "2026-02",
      "total_sales": 45000.0,
      "total_expenses": 12000.0,
      "net_income": 33000.0,
      "transaction_count": 18,
      "daily_breakdown": [
        { "date": "2026-02-01", "sales": 1500.0, "expenses": 200.0 }
      ],
      "expense_by_category": { "food_supplies": 8000.0, "rent": 4000.0 }
    }
  }
}
```

---

## 6. Evidence / OCR (`/evidence`)

### `POST /evidence/upload` — Upload evidence photo

**Auth:** Client or CA
**Content-Type:** `multipart/form-data`

| Field | Required | Notes |
|-------|----------|-------|
| `file` | Yes | JPG/PNG/PDF/WebP, max 10MB |
| `business_id` | CA only | Which client |
| `statement_id` | No | Link to a transaction |

**Response (202):**
```json
{
  "data": {
    "evidence_id": 55,
    "file_url": "https://res.cloudinary.com/...",
    "thumbnail_url": "https://res.cloudinary.com/.../w_300,h_300/...",
    "quality_score": 87.3,
    "quality_status": "good",       // "good" | "low_quality" | "rejected"
    "ocr_status": "pending",        // "pending" | "processing" | "success" | "failed"
    "quality_warning": null,
    "message": "Photo saved. Scanning for details..."
  }
}
```

**Frontend:** Poll `GET /evidence/<id>` until `ocr_status` is `"success"` or `"failed"`.

---

### `GET /evidence/<id>` — Evidence details

**Response:**
```json
{
  "data": {
    "id": 55, "business_id": 15, "statement_id": 101,
    "file_url": "https://...", "thumbnail_url": "https://...",
    "quality_score": 87.3, "quality_status": "good",
    "ocr_status": "success",
    "ocr_amount": 2500.0,
    "ocr_date": "2026-02-26",
    "ocr_vendor_name": "Daily Mart",
    "ocr_document_type": "invoice",
    "strength": "strong"            // "strong" | "medium" | "weak"
  }
}
```

---

### `GET /evidence/clients/<business_id>` — CA: list evidence for a client

**Query:** `?strength=weak&ocr_status=failed&page=1&per_page=20`

---

## 7. Dashboard (`/dashboard`)

### `GET /dashboard` — CA main dashboard

**Auth:** CA role only (clients get 403)

**Response:**
```json
{
  "data": {
    "org_name": "Nair & Associates",
    "stats": {
      "total_clients": 25,
      "active_clients": 18,
      "invited_not_joined": 5,
      "red_clients": 8,
      "yellow_clients": 6,
      "green_clients": 11,
      "unread_alerts": 3
    },
    "clients": [
      {
        "id": 15, "name": "Ram Prasad Tea Stall",
        "business_type": "food", "phone": "9876543210",
        "invite_status": "active",
        "compliance_color": "red",
        "compliance_score": 42.0,
        "days_since_last_entry": 7,
        "last_transaction_at": "2026-02-20",
        "transactions_this_month": 3
      }
    ],
    "recent_alerts": [
      {
        "id": 9, "alert_type": "gst_threshold",
        "severity": "high",
        "title": "Turnover approaching GST threshold",
        "created_at": "2026-02-26T08:00:00"
      }
    ]
  }
}
```

**Sort order:** Red clients first → Yellow → Green. Within same color, sorted by `days_since_last_entry` descending (most neglected first).

---

## 8. Compliance Engine (`/compliance`)

> **Note:** These endpoints return **raw JSON** (no `success`/`data`/`error` envelope).

### `GET /compliance/orgs/<org_id>/risk-summary`

```json
{
  "organization_id": 7, "organization_name": "Nair & Associates",
  "total_businesses": 25,
  "risky_businesses": {
    "count": 4,
    "list": [
      { "business_id": 15, "business_name": "...", "discipline_score": 38.5,
        "evidence_health": 42.0, "estimated_turnover": 480000,
        "gst_risk_level": "low" }
    ]
  },
  "approaching_gst_threshold": {
    "count": 2,
    "list": [ { "business_id": 20, "estimated_turnover": 2200000, "gst_risk_level": "high" } ]
  },
  "weak_evidence_businesses": { "count": 3, "list": [ ... ] },
  "open_alerts_summary": { "critical": 1, "high": 3, "medium": 5, "low": 2, "total": 11 }
}
```

GST thresholds: `>= 20L (2,000,000)` = must register, `>= 40L (4,000,000)` = certain sectors.

---

### `GET /compliance/businesses/<business_id>/profile`

```json
{
  "business_id": 15, "business_name": "...",
  "profile": {
    "discipline_score": 38.5,     // 0-100 (higher = more compliant)
    "evidence_health": 42.0,      // 0-100
    "estimated_turnover": 480000,
    "gst_risk_level": "low",      // "low" | "medium" | "high" | "critical"
    "last_updated": "2026-02-26T08:00:00"
  },
  "latest_signal": {
    "signal_date": "2026-02-26", "daily_turnover": 2500,
    "monthly_turnover": 45000, "evidence_ratio": 66.7,
    "silence_days": 1, "abnormal_spike_detected": false
  },
  "open_alerts": { "count": 2, "alerts": [ ... ] }
}
```

---

### `GET /compliance/orgs/<org_id>/alerts/open`

**Query:** `?severity=high&business_id=15&alert_type=gst_threshold`

---

### `POST /compliance/compliance/alerts/<alert_id>/acknowledge`

> **URL NOTE:** The path has `/compliance/compliance/` (doubled) due to blueprint prefix.

### `POST /compliance/compliance/alerts/<alert_id>/resolve`

---

### `GET /compliance/orgs/<org_id>/discipline-ranking`

Returns `top_compliant` and `bottom_compliant` arrays (up to 10 each).

---

### `GET /compliance/orgs/<org_id>/summary`

Org-level statistics: total businesses, statements, evidence, confidence breakdown.

---

## 9. Reminders (`/reminders`)

### `POST /reminders/send` — Send push notifications

**Auth:** CA role only

**Request:**
```json
{
  "client_ids": [15, 20, 22],     // list of business IDs, or "all"
  "message": "Please upload this week's bills.",   // required, max 500 chars
  "type": "general"               // optional: "deadline" | "general" | "missing" | "urgent"
}
```

**Response:**
```json
{
  "data": {
    "sent": 2, "failed": 0, "skipped": 1, "total": 3,
    "details": [
      { "client_id": 15, "client_name": "Ram Prasad", "status": "delivered" },
      { "client_id": 20, "client_name": "...", "status": "no_token", "reason": "Device not registered" },
      { "client_id": 22, "client_name": "...", "status": "skipped", "reason": "No user account linked" }
    ]
  }
}
```

---

### `POST /reminders/send-bulk` — Bulk with deadline context

Same as `/send` but includes `deadline_type` field. When provided, the message includes the actual due date and marks the deadline as "reminded".

```json
{
  "client_ids": "all",
  "message": "File your GSTR-1 today!",
  "deadline_type": "gstr1_monthly"
}
```

---

## 10. Deadlines / Calendar (`/deadlines`)

### `GET /deadlines/clients/<business_id>` — Client's deadlines

**Auth:** CA (same org) or Client (own business)
**Query:** `?status=pending` (pending / reminded / acknowledged / completed / missed)

**Response:**
```json
{
  "data": {
    "client": { "id": 15, "name": "...", "gstin": "...", "business_type": "food" },
    "deadlines": [
      {
        "id": 7,
        "deadline_type": "gstr3b",
        "description": "GSTR-3B Filing -- Feb 2026",
        "due_date": "2026-03-20",
        "period_start": "2026-02-01",
        "period_end": "2026-02-28",
        "status": "pending",
        "reminder_sent_at": null,
        "acknowledged_at": null,
        "completed_at": null,
        "completed_by": null,
        "notes": null
      }
    ],
    "summary": {
      "total": 12, "pending": 8, "reminded": 2,
      "acknowledged": 1, "completed": 1, "missed": 0, "overdue": 0
    }
  }
}
```

### Deadline Types

| Type | Filing | Due Date |
|------|--------|----------|
| `gstr1_monthly` | GSTR-1 Monthly | 11th of next month |
| `gstr1_quarterly` | GSTR-1 Quarterly (QRMP) | 13th of month after quarter |
| `gstr3b` | GSTR-3B | 20th of next month |
| `cmp08` | CMP-08 (Composition) | 18th of month after quarter |
| `advance_tax_q1` | Advance Tax Q1 | June 15 |
| `advance_tax_q2` | Advance Tax Q2 | September 15 |
| `advance_tax_q3` | Advance Tax Q3 | December 15 |
| `advance_tax_q4` | Advance Tax Q4 | March 15 |
| `fssai_renewal` | FSSAI License Renewal | 30 days before expiry |

### Status Flow

```
pending → reminded → acknowledged → completed
                  ↘ missed (auto, if past due_date)
```

---

### `GET /deadlines/upcoming` — CA overview

**Query:** `?days=30` (1-90, default 30)

**Response:**
```json
{
  "data": {
    "period": { "from": "2026-02-27", "to": "2026-03-29", "days": 30 },
    "overdue": [ { ... , "days_overdue": 3 } ],
    "this_week": [ { ... , "client_name": "..." } ],
    "next_week": [ ... ],
    "later": [ ... ],
    "summary": {
      "total_upcoming": 15, "overdue": 2,
      "this_week": 4, "next_week": 5, "later": 6,
      "unique_clients": 10
    }
  }
}
```

---

### `POST /deadlines/<id>/complete` — CA marks deadline as filed

**Request (optional):** `{ "notes": "Filed via GST portal on 27-Feb" }`

**Errors:** 400 (already completed), 403 (wrong org)

---

### `POST /deadlines/<id>/acknowledge` — Client acknowledges

No body needed.

**Errors:** 400 (already completed/missed), 403 (wrong business)

---

### `POST /deadlines/generate/<business_id>` — Generate deadlines

Generates up to 12 months of deadlines based on client's GST scheme. Idempotent — safe to call multiple times.

**Response (201 or 200):**
```json
{ "data": { "client_id": 15, "deadlines_created": 14, "message": "Generated 14 new deadline(s)." } }
```

**Auto-generation rules:**
- Has GSTIN + turnover > 5Cr → GSTR-1 monthly + GSTR-3B
- Has GSTIN + turnover <= 5Cr → GSTR-1 quarterly + GSTR-3B
- All clients → Advance Tax Q1-Q4
- Food sector → FSSAI renewal

---

## 11. Validation / Anomaly Detection (`/validation`)

### `POST /validation/check` — Dry-run validation

Validates a transaction WITHOUT creating it. Use before submitting.

**Auth:** Client (auto-uses own business) or CA (must provide `business_id`)

**Request:**
```json
{
  "amount": 250000.0,              // required
  "type": "sale",                  // required: "sale" | "expense"
  "transaction_date": "2026-02-27",  // optional
  "business_id": 15                // required for CA only
}
```

**Response:**
```json
{
  "data": {
    "warnings": [
      {
        "rule": "outlier_detection",
        "message": "Amount is 6x your 30-day average",
        "severity": "medium",
        "details": { "average": 5000, "ratio": 6.0 }
      }
    ],
    "warning_count": 1,
    "valid": true       // false if any severity="high"
  }
}
```

### Validation Rules

| Rule | Triggers When | Severity |
|------|--------------|----------|
| `amount_range` | Amount < 0 or > 1 Crore (10,000,000) | high |
| `future_date` | Transaction date is in the future | high |
| `outlier_detection` | Amount > 5x the 30-day rolling average | medium |
| `duplicate_detection` | Same amount + type on the same day | low |

---

### `GET /validation/clients/<business_id>/anomalies` — Anomaly summary

**Auth:** CA role only

**Response:**
```json
{
  "data": {
    "client_name": "Ram Prasad Tea Stall",
    "gap_days": 2,
    "gap_status": "ok",             // "ok" | "warning" | "critical"
    "outlier_count_30d": 1,
    "duplicate_count_30d": 2,
    "flagged_transactions": [ ... ],
    "averages": {
      "sale_avg_30d": 5000.0,
      "expense_avg_30d": 2000.0
    }
  }
}
```

---

## 12. WhatsApp (`/whatsapp`)

### Webhook (Public)

- `GET /whatsapp/webhook` — Meta verification handshake
- `POST /whatsapp/webhook` — Receive messages (always returns 200)
- `POST /whatsapp/webhook/status` — Delivery receipts

### Message History

- `GET /whatsapp/businesses/<id>/messages?status=parsed&limit=50`
- `GET /whatsapp/messages/<id>` — Single message detail

**Message statuses:** `received` → `parsed` → `statement_created` (or `parse_failed`)

---

## 13. Rate Limit Reference

| Endpoint | Limit |
|----------|-------|
| **Default (all routes)** | **200/hour per IP** |
| `POST /auth/register` | 5/hour |
| `POST /auth/verify-otp` | 10/min |
| `POST /auth/resend-otp` | 5/hour + 60s cooldown |
| `POST /auth/login` | 10/min |
| `POST /auth/refresh` | 30/min |
| `POST /clients` | 60/hour |
| `PUT /clients/<id>` | 120/hour |
| `POST /clients/<id>/regenerate-invite` | 20/hour |
| `GET /clients/<id>/filing-summary/export` | 20/hour |
| `GET /invite/<code>` | 30/min |
| `POST /invite/accept` | 10/min |
| `POST /invite/verify-otp` | 10/min |
| `POST /transactions` | 200/day, 30/hour |
| `POST /evidence/upload` | 100/day, 20/hour |
| `POST /reminders/send` | 30/hour, 200/day |
| `POST /reminders/send-bulk` | 20/hour, 100/day |

**Rate limit headers:** `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`

---

## 14. Global Error Codes

| HTTP | Meaning | Frontend Action |
|------|---------|-----------------|
| 400 | Bad request / validation error | Show field-level errors |
| 401 | Auth required / token expired | Refresh token or redirect to login |
| 403 | Insufficient permissions | Show "Access denied" |
| 404 | Resource not found | Show "Not found" |
| 409 | Duplicate resource | Show "Already exists" |
| 410 | Invite expired | Show "Link expired, ask CA for new one" |
| 429 | Rate limited | Show "Too many requests" + retry after |
| 500 | Server error | Show generic error, retry |

---

## 15. Recommended UI Flows

### CA Registration Flow

```
Register Page (/register)
  ↓ POST /auth/register
OTP Verification (/verify?user_id=42)
  ↓ POST /auth/verify-otp
  ↓ Store tokens in localStorage/cookie
Dashboard (/dashboard)
  ↓ GET /dashboard
```

### Client Onboarding Flow

```
Invite Link (/invite/xK3mP9)
  ↓ GET /invite/xK3mP9 (show CA firm name)
Accept Form
  ↓ POST /invite/accept (name, phone, pin)
OTP Verification
  ↓ POST /invite/verify-otp
  ↓ Store tokens
Client Dashboard (/my/summary)
```

### Transaction Entry Flow (Client)

```
Transaction Form
  ↓ (Optional) POST /validation/check → show warnings inline
  ↓ POST /transactions (with or without photo)
  ↓
  ├── No issues → Show success toast
  ├── duplicate_warning → Show "Similar entry" toast (non-blocking)
  ├── quality_warning → Show "Retake photo" suggestion
  ├── ocr_result.conflict → Show conflict dialog
  │     ↓ User picks amount
  │     ↓ PATCH /transactions/<id>
  └── warnings[] → Show warning badges
```

### CA Dashboard Flow

```
Dashboard (/dashboard)
  ↓ GET /dashboard
  ↓ Click client card
Client Detail (/clients/15/detail)
  ↓ GET /clients/15/detail
  ↓
  ├── View transactions → GET /compliance/businesses/15/statements
  ├── View evidence → GET /compliance/businesses/15/evidence
  ├── View compliance → GET /compliance/businesses/15/profile
  ├── View deadlines → GET /deadlines/clients/15
  ├── View anomalies → GET /validation/clients/15/anomalies
  └── Filing summary → GET /clients/15/filing-summary?month=2026-02
       ↓ Export → GET /clients/15/filing-summary/export
```

### Deadline Management Flow (CA)

```
Calendar View (/deadlines)
  ↓ GET /deadlines/upcoming?days=30
  ↓
  ├── Generate for new client → POST /deadlines/generate/15
  ├── View client deadlines → GET /deadlines/clients/15
  ├── Mark as filed → POST /deadlines/7/complete
  └── Send reminders → POST /reminders/send-bulk
```

### Compliance Overview Flow (CA)

```
Risk Dashboard (/compliance)
  ↓ GET /compliance/orgs/7/risk-summary
  ↓
  ├── Ranking → GET /compliance/orgs/7/discipline-ranking
  ├── Alerts → GET /compliance/orgs/7/alerts/open
  │     ├── Acknowledge → POST /compliance/compliance/alerts/9/acknowledge
  │     └── Resolve → POST /compliance/compliance/alerts/9/resolve
  └── Client drill-down → GET /compliance/businesses/15/profile
```

---

## Appendix: Suggested Page Structure

### CA App Pages

| Page | Primary API | Secondary APIs |
|------|------------|----------------|
| Login | `POST /auth/login` | |
| Register | `POST /auth/register` → `POST /auth/verify-otp` | |
| Dashboard | `GET /dashboard` | |
| Client List | `GET /clients` | |
| Add Client | `POST /clients` | |
| Client Detail | `GET /clients/<id>/detail` | `GET /deadlines/clients/<id>`, `GET /validation/clients/<id>/anomalies` |
| Filing Summary | `GET /clients/<id>/filing-summary` | `GET /clients/<id>/filing-summary/export` |
| Compliance Risk | `GET /compliance/orgs/<id>/risk-summary` | `GET /compliance/orgs/<id>/discipline-ranking` |
| Alerts | `GET /compliance/orgs/<id>/alerts/open` | |
| Deadline Calendar | `GET /deadlines/upcoming` | `POST /deadlines/generate/<id>` |
| Send Reminders | `POST /reminders/send` | `POST /reminders/send-bulk` |

### Client App Pages

| Page | Primary API | Secondary APIs |
|------|------------|----------------|
| Invite Accept | `GET /invite/<code>` → `POST /invite/accept` → `POST /invite/verify-otp` | |
| My Dashboard | `GET /my/summary` | |
| Add Transaction | `POST /transactions` | `POST /validation/check` |
| My Transactions | `GET /my/transactions` | |
| My Deadlines | `GET /deadlines/clients/<id>` | `POST /deadlines/<id>/acknowledge` |
| Upload Evidence | `POST /evidence/upload` | `GET /evidence/<id>` |

---

## Appendix: Environment Variables (Backend Reference)

| Variable | Purpose |
|----------|---------|
| `SECRET_KEY` | Flask secret |
| `JWT_SECRET_KEY` | JWT signing key |
| `DATABASE_URL` | DB connection (default: SQLite) |
| `GOOGLE_API_KEY` | Gemini Vision OCR |
| `CLOUDINARY_URL` | Evidence file storage |
| `WHATSAPP_VERIFY_TOKEN` | Webhook verification |
| `FCM_SERVER_KEY` | Push notifications |

---

*Generated for BharatCompliance v2 — All 7 features implemented.*
