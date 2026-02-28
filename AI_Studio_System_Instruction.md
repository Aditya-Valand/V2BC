# BharatCompliance — Frontend AI System Instruction

Paste this entire document as the system instruction in AI Studio before building any frontend code.

---

## Project Identity

You are building the frontend for **BharatCompliance** — a WhatsApp-first financial compliance SaaS for India's micro-businesses (street vendors, gig workers, freelancers). CA (Chartered Accountant) firms use it to manage client compliance.

**Backend API base URL:**
- Dev: `http://localhost:5000`
- Prod: `https://bharatcomplianceb.onrender.com`

---

## Tech Stack (FIXED — never suggest alternatives)

| Concern | Tool |
|---------|------|
| Framework | Next.js 14+ (App Router) |
| Language | **JavaScript only — NO TypeScript** |
| Styling | Tailwind CSS |
| UI Primitives | Radix UI (`@radix-ui/react-*`) |
| Icons | `lucide-react` |
| HTTP client | `axios` (via `@/lib/api/client.js`) |
| Server state | `@tanstack/react-query` |
| Client state | `zustand` |
| Forms | `react-hook-form` + `zod` |
| Tables | `@tanstack/react-table` |
| Charts | `recharts` |
| Toasts | `sonner` |
| Date utils | `date-fns` |
| File upload | `react-dropzone` |
| Class merging | `clsx` + `tailwind-merge` via `cn()` from `@/lib/utils` |

---

## Absolute Folder Structure

```
frontend/
├── src/
│   ├── app/
│   │   ├── (auth)/                  ← Login, Register, OTP, Invite pages
│   │   │   ├── layout.js
│   │   │   ├── login/page.js
│   │   │   ├── register/page.js
│   │   │   ├── verify-otp/page.js
│   │   │   └── invite/[code]/page.js
│   │   ├── (ca)/                    ← CA dashboard group (sidebar layout)
│   │   │   ├── layout.js
│   │   │   ├── dashboard/page.js
│   │   │   ├── clients/
│   │   │   │   ├── page.js           ← Client list
│   │   │   │   └── [id]/
│   │   │   │       ├── page.js       ← Client overview redirect
│   │   │   │       ├── detail/page.js
│   │   │   │       ├── deadlines/page.js
│   │   │   │       └── filing/page.js
│   │   │   ├── compliance/page.js
│   │   │   ├── deadlines/page.js
│   │   │   └── reminders/page.js
│   │   ├── (client)/                ← Client app group (mobile-first layout)
│   │   │   ├── layout.js
│   │   │   ├── home/page.js
│   │   │   ├── transactions/
│   │   │   │   ├── page.js
│   │   │   │   └── new/page.js
│   │   │   ├── deadlines/page.js
│   │   │   └── evidence/page.js
│   │   ├── providers.js             ← QueryClient + Toaster
│   │   ├── layout.js                ← Root layout
│   │   └── page.js                  ← Root redirect based on role
│   ├── components/
│   │   ├── ui/                      ← Base reusable atoms (Button, Badge, Card, Modal, etc.)
│   │   ├── auth/                    ← Auth-specific components
│   │   ├── ca/
│   │   │   ├── dashboard/           ← Dashboard-specific components
│   │   │   ├── clients/             ← Client list/card/detail components
│   │   │   ├── compliance/          ← Compliance charts, alert cards
│   │   │   └── deadlines/           ← Deadline calendar, deadline row
│   │   ├── client/
│   │   │   ├── transactions/        ← Transaction form, list, warning banner
│   │   │   └── deadlines/           ← Client deadline card
│   │   └── shared/
│   │       ├── layout/              ← Sidebar, Topbar, BottomNav, PageHeader
│   │       └── forms/               ← FormField wrapper, PhoneInput, AmountInput
│   ├── lib/
│   │   ├── api/
│   │   │   ├── client.js            ← Axios instance + token refresh + getApiError()
│   │   │   ├── auth.js
│   │   │   ├── clients.js
│   │   │   ├── transactions.js
│   │   │   ├── evidence.js
│   │   │   ├── dashboard.js
│   │   │   ├── compliance.js
│   │   │   ├── deadlines.js
│   │   │   ├── reminders.js
│   │   │   ├── validation.js
│   │   │   └── index.js             ← Re-exports all api modules
│   │   ├── utils.js                 ← cn(), formatINR(), formatDate(), timeAgo(), getInitials(), downloadBlob()
│   │   └── validators/              ← Zod schemas for forms
│   ├── hooks/                       ← Custom React hooks (useAuth, useTransactions, etc.)
│   ├── store/
│   │   └── authStore.js             ← Zustand auth store
│   ├── constants/
│   │   └── index.js                 ← COMPLIANCE_COLORS, DEADLINE_TYPES, DEADLINE_STATUS, formatINR, etc.
│   └── middleware.js                ← Route protection
```

---

## Non-Negotiable Coding Rules

### 1. Always JavaScript — Never TypeScript
- All files end in `.js` or `.jsx`
- No `type`, `interface`, `: string`, generics, or `as` casts
- Use JSDoc comments for documentation if needed

### 2. Always use the existing API layer
- **Never** write raw `fetch()` or `axios.create()` in components
- Always import from `@/lib/api/*`

```js
// CORRECT
import { authApi } from "@/lib/api/auth";
import { clientsApi } from "@/lib/api/clients";

// WRONG
import axios from "axios";
const res = await axios.get("http://localhost:5000/clients");
```

### 3. Always use `getApiError()` for error handling

```js
import { getApiError } from "@/lib/api/client";

try {
  const res = await authApi.login(email, password);
} catch (err) {
  toast.error(getApiError(err));
}
```

### 4. Always use Zustand auth store for user/token state

```js
import useAuthStore from "@/store/authStore";

const { user, org, isAuthenticated, getRole, isCA, isClient } = useAuthStore();
const setAuth = useAuthStore((s) => s.setAuth);
const logout = useAuthStore((s) => s.logout);
```

### 5. Use React Query for all server data fetching

```js
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { clientsApi } from "@/lib/api/clients";

// Query
const { data, isLoading, error } = useQuery({
  queryKey: ["clients"],
  queryFn: () => clientsApi.list().then(r => r.data.data),
});

// Mutation
const mutation = useMutation({
  mutationFn: (data) => clientsApi.create(data),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ["clients"] });
    toast.success("Client added!");
  },
  onError: (err) => toast.error(getApiError(err)),
});
```

### 6. Use `cn()` from `@/lib/utils` for Tailwind class merging

```js
import { cn } from "@/lib/utils";
<div className={cn("base-class", isActive && "active-class")} />
```

### 7. Use `formatINR()` for ALL currency display

```js
import { formatINR } from "@/lib/utils";
<span>{formatINR(45000)}</span>  // → ₹45,000
```

### 8. Use sonner for ALL toasts

```js
import { toast } from "sonner";
toast.success("Done!");
toast.error("Something failed.");
toast.info("FYI...");
```

### 9. "use client" directive — know when to use it
- Add `"use client"` at the top of any file that uses: `useState`, `useEffect`, `useRouter`, `onClick`, form handlers, or any hook
- Server components (no directive needed): static layouts, data-fetching wrappers
- When in doubt for interactive pages → always add `"use client"`

### 10. Import alias — always use `@/` not relative paths

```js
// CORRECT
import { cn } from "@/lib/utils";
import useAuthStore from "@/store/authStore";

// WRONG
import { cn } from "../../lib/utils";
```

---

## API Response Envelope

All API responses (except `/compliance/*`) follow this shape:

```json
{ "success": true, "data": { ... }, "error": null }
```

Always access `.data.data` from axios responses:

```js
const res = await authApi.login(email, password);
const { access_token, user, org } = res.data.data;
```

The `/compliance/*` endpoints return raw JSON — access `.data` directly:

```js
const res = await complianceApi.riskSummary(orgId);
const { total_businesses, risky_businesses } = res.data;
```

---

## Auth Flow Summary

### CA Registration
```
POST /auth/register → returns { user_id, otp_dev_only }
→ navigate to /verify-otp?user_id=42
POST /auth/verify-otp → returns { access_token, refresh_token, user, org }
→ call setAuth() → navigate to /dashboard
```

### CA Login
```
POST /auth/login → returns { access_token, refresh_token, user, org }
→ call setAuth() → navigate to /dashboard
```

### Client Invite
```
GET /invite/:code → show CA firm name
POST /invite/accept { invite_code, name, phone, pin } → returns { user_id, otp_dev_only }
POST /invite/verify-otp → returns { access_token, refresh_token, user, business }
→ call setAuth() → navigate to /home
```

### setAuth() stores tokens in localStorage AND Zustand:
```js
setAuth({
  user: data.user,
  org: data.org,
  access_token: data.access_token,
  refresh_token: data.refresh_token,
});
```

---

## Two App Contexts

### CA App (routes under `(ca)/`)
- Sidebar navigation layout
- Can access: dashboard, all clients, compliance, deadlines, reminders
- Token has: `role: "ca_owner" | "ca_staff"`, `org_id`
- Guard: redirect to `/login` if not CA

### Client App (routes under `(client)/`)
- Mobile-first bottom navigation layout
- Can access: home (summary), transactions, deadlines, evidence
- Token has: `role: "client"`, `business_id`, `org_id`
- Guard: redirect to `/login` if not client

---

## Key Data Shapes (most used)

### Transaction (from POST /transactions)
```js
{
  transaction: { id, type, amount, category, description, transaction_date, confidence_level, evidence_id },
  duplicate_warning: null | { message, existing_id },
  ocr_result: null | { conflict: true, entered_amount, ocr_amount, message },
  quality_warning: null | "string",
  warnings: [{ rule, message, severity, details }]
}
```

### Warning rules: `amount_range`, `future_date`, `outlier_detection`, `duplicate_detection`
### Severity: `"high"` (blocks valid=false), `"medium"`, `"low"`

### Client card (from GET /dashboard → clients[])
```js
{
  id, name, business_type, phone, invite_status,
  compliance_color: "red" | "yellow" | "green",
  compliance_score,       // 0-100
  days_since_last_entry,
  last_transaction_at,
  transactions_this_month
}
```

### Deadline
```js
{
  id, deadline_type, description, due_date,
  period_start, period_end,
  status: "pending" | "reminded" | "acknowledged" | "completed" | "missed",
  reminder_sent_at, acknowledged_at, completed_at, notes
}
```

### Compliance alert
```js
{
  id, alert_type, severity: "critical" | "high" | "medium" | "low",
  reason, rule_triggered, status: "open" | "acknowledged" | "resolved",
  created_at
}
```

---

## Constants to always import from `@/constants`

```js
import {
  COMPLIANCE_COLORS,    // { green, yellow, red } → { label, bg, text, dot }
  DEADLINE_TYPES,       // { gstr3b: "GSTR-3B", ... }
  DEADLINE_STATUS,      // { pending, reminded, acknowledged, completed, missed }
  ALERT_SEVERITY,       // { critical, high, medium, low }
  EVIDENCE_STRENGTH,    // { strong, medium, weak }
  TX_TYPES,             // [{ value, label }]
  REMINDER_TYPES,       // [{ value, label }]
} from "@/constants";
```

---

## Page Creation Checklist

When creating a new page, always:

1. Start with `"use client"` if it has any interactivity
2. Import API module from `@/lib/api/*`
3. Use `useQuery` for data fetching
4. Use `useMutation` for form submissions
5. Show loading state (spinner or skeleton)
6. Show error state with a retry option
7. Use `toast.error(getApiError(err))` in all catch blocks
8. Use `formatINR()` for all money values
9. Use `formatDate()` from `@/lib/utils` for dates

---

## Component Naming Conventions

| Type | Convention | Example |
|------|-----------|---------|
| Page | `page.js` in folder | `app/(ca)/dashboard/page.js` |
| Layout | `layout.js` in folder | `app/(ca)/layout.js` |
| Feature component | PascalCase `.js` | `ClientCard.js` |
| Shared UI atom | PascalCase `.js` in `components/ui/` | `Button.js`, `Badge.js` |
| Custom hook | `use` prefix | `useClientDetail.js` |
| API module | camelCase + Api suffix | `clientsApi`, `authApi` |
| Zustand store | camelCase + Store suffix | `authStore.js` |

---

## Indian-Specific UX Rules

- All currency: **₹ Indian Rupees** via `formatINR()` from `@/lib/utils`
- Phone numbers: 10-digit Indian mobile format
- GSTIN: shown as-is (15 chars)
- GST thresholds: ₹20 Lakh = `₹20,00,000`, ₹40 Lakh = `₹40,00,000`
- Compliance color system: green = good, yellow = needs attention, red = urgent
- Dates: dd MMM yyyy format (e.g. "27 Feb 2026")
- Default language: English (future: Hindi support planned)

---

## What NOT to do

- Do NOT use TypeScript (no `.ts`, `.tsx`, no `type`, no `interface`)
- Do NOT use `fetch()` directly — always use `@/lib/api/*`
- Do NOT install new packages without listing them — use what's already installed
- Do NOT use CSS modules — use Tailwind only
- Do NOT put business logic in page files — extract to hooks or service functions
- Do NOT hardcode the API URL — always use `process.env.NEXT_PUBLIC_API_URL`
- Do NOT use `alert()` or `console.log()` in final code
- Do NOT import from relative paths like `../../` — always use `@/`

---

## Installed Packages (do not reinstall)

```
next, react, react-dom
tailwindcss, postcss, autoprefixer
axios
zustand
@tanstack/react-query
@tanstack/react-table
react-hook-form
@hookform/resolvers
zod
sonner
lucide-react
clsx
tailwind-merge
class-variance-authority
date-fns
recharts
react-dropzone
jose
prettier
prettier-plugin-tailwindcss
@radix-ui/react-dialog
@radix-ui/react-dropdown-menu
@radix-ui/react-label
@radix-ui/react-select
@radix-ui/react-separator
@radix-ui/react-slot
@radix-ui/react-tabs
@radix-ui/react-toast
@radix-ui/react-tooltip
@radix-ui/react-avatar
@radix-ui/react-progress
@radix-ui/react-switch
@radix-ui/react-checkbox
@radix-ui/react-popover
@radix-ui/react-accordion
```

---

*This instruction governs all frontend code for BharatCompliance. Follow it exactly.*
