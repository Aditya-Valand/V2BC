"use client";

import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Send, Users, CheckSquare, Square, Search,
  MessageSquare, CheckCircle2, XCircle, SkipForward,
  ChevronDown,
} from "lucide-react";
import { toast } from "sonner";
import { remindersApi } from "@/lib/api/reminders";
import { clientsApi } from "@/lib/api/clients";
import { getApiError } from "@/lib/api/client";
import { COMPLIANCE_COLORS, REMINDER_TYPES, DEADLINE_TYPES } from "@/constants";
import { getInitials } from "@/lib/utils";

// ── Constants ─────────────────────────────────────────────────────────

const MAX_MSG = 500;

const DEADLINE_TYPE_OPTIONS = [
  { value: "",                  label: "No specific deadline" },
  { value: "gstr1_monthly",     label: "GSTR-1 Monthly" },
  { value: "gstr1_quarterly",   label: "GSTR-1 Quarterly" },
  { value: "gstr3b",            label: "GSTR-3B" },
  { value: "cmp08",             label: "CMP-08" },
  { value: "advance_tax_q1",    label: "Advance Tax Q1" },
  { value: "advance_tax_q2",    label: "Advance Tax Q2" },
  { value: "advance_tax_q3",    label: "Advance Tax Q3" },
  { value: "advance_tax_q4",    label: "Advance Tax Q4" },
  { value: "fssai_renewal",     label: "FSSAI Renewal" },
];

const DEFAULT_MESSAGES = {
  general:  "A reminder from your CA. Please ensure your records are up to date.",
  deadline: "This is a reminder for an upcoming filing deadline. Please prepare your documents.",
  missing:  "We noticed some transactions are missing for this period. Please upload the relevant receipts.",
  urgent:   "Urgent: Immediate attention required for compliance. Please contact us.",
};

// ── Client Selector ───────────────────────────────────────────────────

function ClientSelector({ clients, selected, onToggle, onSelectAll, onClearAll }) {
  const [search, setSearch] = useState("");
  const filtered = useMemo(() => {
    if (!search.trim()) return clients;
    const q = search.toLowerCase();
    return clients.filter(
      (c) => c.name.toLowerCase().includes(q) || c.phone?.includes(q),
    );
  }, [clients, search]);

  const allSelected = selected.size === clients.filter((c) => c.invite_status === "active").length;

  return (
    <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
        <span className="text-sm font-semibold text-slate-700">
          Select Recipients
          {selected.size > 0 && (
            <span className="ml-2 text-xs font-medium text-blue-600 bg-blue-50 px-2 py-0.5 rounded-full">
              {selected.size} selected
            </span>
          )}
        </span>
        <button
          onClick={allSelected ? onClearAll : onSelectAll}
          className="text-xs font-semibold text-blue-700 hover:underline flex items-center gap-1"
        >
          {allSelected ? <><Square size={12} /> Clear all</> : <><CheckSquare size={12} /> Select all</>}
        </button>
      </div>

      {/* Search */}
      <div className="px-3 py-2 border-b border-slate-100">
        <div className="relative">
          <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search clients…"
            className="w-full pl-8 pr-3 py-1.5 text-sm bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:border-blue-400"
          />
        </div>
      </div>

      {/* List */}
      <div className="max-h-64 overflow-y-auto divide-y divide-slate-100">
        {filtered.length === 0 ? (
          <p className="px-4 py-6 text-sm text-slate-400 text-center">No active clients found.</p>
        ) : filtered.map((c) => {
          const isActive  = c.invite_status === "active";
          const isChecked = selected.has(c.id);
          const cc = COMPLIANCE_COLORS[c.compliance_color] || COMPLIANCE_COLORS.green;

          return (
            <button
              key={c.id}
              onClick={() => isActive && onToggle(c.id)}
              disabled={!isActive}
              className={`w-full flex items-center gap-3 px-4 py-2.5 transition-colors text-left ${
                isActive ? "hover:bg-slate-50" : "opacity-40 cursor-not-allowed"
              } ${isChecked ? "bg-blue-50" : ""}`}
            >
              {/* Checkbox */}
              <div className={`w-5 h-5 rounded-md border-2 flex items-center justify-center shrink-0 transition-colors ${
                isChecked ? "bg-blue-700 border-blue-700" : "border-slate-300"
              }`}>
                {isChecked && <CheckSquare size={12} className="text-white" strokeWidth={3} />}
              </div>
              {/* Avatar */}
              <div className="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center shrink-0">
                <span className="text-xs font-bold text-slate-600">{getInitials(c.name)}</span>
              </div>
              {/* Info */}
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-slate-700 truncate">{c.name}</p>
                {c.phone && <p className="text-xs text-slate-400">{c.phone}</p>}
              </div>
              {/* Status */}
              <div className="shrink-0 flex items-center gap-1.5">
                <span className={`w-2 h-2 rounded-full ${cc.dot}`} />
                {!isActive && <span className="text-[10px] text-slate-400">Pending</span>}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

// ── Result card ───────────────────────────────────────────────────────

function ResultCard({ result, onReset }) {
  const { sent, failed, skipped, total, details = [] } = result;

  return (
    <div className="space-y-5">
      <div className="bg-white rounded-2xl border border-slate-200 p-5">
        <div className="flex items-center gap-3 mb-5">
          <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center">
            <CheckCircle2 size={24} className="text-green-600" />
          </div>
          <div>
            <h2 className="text-base font-bold text-slate-800">Reminders Sent</h2>
            <p className="text-xs text-slate-400">{total} total recipients</p>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-3 mb-4">
          {[
            { label: "Delivered", value: sent,    icon: CheckCircle2, color: "text-green-700 bg-green-50" },
            { label: "Failed",    value: failed,  icon: XCircle,      color: "text-red-700 bg-red-50"     },
            { label: "Skipped",   value: skipped, icon: SkipForward,  color: "text-slate-600 bg-slate-100"},
          ].map(({ label, value, icon: Icon, color }) => (
            <div key={label} className={`rounded-xl p-3 text-center ${color}`}>
              <Icon size={16} className="mx-auto mb-1 opacity-60" />
              <p className="text-xl font-bold">{value}</p>
              <p className="text-[11px] opacity-70">{label}</p>
            </div>
          ))}
        </div>

        {details.length > 0 && (
          <div className="bg-slate-50 rounded-xl divide-y divide-slate-200 max-h-52 overflow-y-auto">
            {details.map((d) => (
              <div key={d.client_id} className="flex items-center justify-between px-3 py-2">
                <span className="text-xs font-medium text-slate-700">{d.client_name}</span>
                <span className={`text-[11px] font-semibold ${
                  d.status === "delivered" ? "text-green-600" :
                  d.status === "failed"    ? "text-red-500"   : "text-slate-400"
                }`}>
                  {d.status}
                  {d.reason && ` · ${d.reason}`}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      <button onClick={onReset} className="btn-primary w-full">Send Another Reminder</button>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────

export default function RemindersPage() {
  const [selected,      setSelected]      = useState(new Set());
  const [message,       setMessage]       = useState(DEFAULT_MESSAGES.general);
  const [type,          setType]          = useState("general");
  const [deadlineType,  setDeadlineType]  = useState("");
  const [loading,       setLoading]       = useState(false);
  const [result,        setResult]        = useState(null);

  const { data: clientData, isLoading: clientsLoading } = useQuery({
    queryKey: ["ca-clients"],
    queryFn: () => clientsApi.list().then((r) => r.data.data),
  });

  const allClients   = clientData?.clients || [];
  const activeClients = allClients.filter((c) => c.invite_status === "active");

  const toggle     = (id) => setSelected((s) => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n; });
  const selectAll  = () => setSelected(new Set(activeClients.map((c) => c.id)));
  const clearAll   = () => setSelected(new Set());

  // Update default message when type changes
  const handleTypeChange = (newType) => {
    setType(newType);
    setMessage(DEFAULT_MESSAGES[newType] || "");
  };

  const handleSend = async () => {
    if (selected.size === 0) { toast.error("Select at least one client."); return; }
    if (!message.trim())     { toast.error("Message cannot be empty.");    return; }

    setLoading(true);
    try {
      const payload = {
        client_ids: [...selected],
        message:    message.trim(),
        type,
        ...(deadlineType ? { deadline_type: deadlineType } : {}),
      };

      const fn  = deadlineType ? remindersApi.sendBulk : remindersApi.send;
      const res = await fn(payload);
      setResult(res.data.data);
    } catch (err) {
      toast.error(getApiError(err));
    } finally {
      setLoading(false);
    }
  };

  if (result) {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="mb-5">
          <h1 className="text-xl font-bold text-slate-800">Reminders</h1>
        </div>
        <ResultCard result={result} onReset={() => { setResult(null); clearAll(); }} />
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-xl font-bold text-slate-800">Send Reminders</h1>
        <p className="text-sm text-slate-400 mt-0.5">
          Notify clients via push notification about upcoming deadlines or missing data.
        </p>
      </div>

      <div className="space-y-5">
        {/* Step 1: Select clients */}
        <div>
          <p className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-2">
            Step 1 — Recipients
          </p>
          {clientsLoading ? (
            <div className="h-48 bg-slate-200 animate-pulse rounded-2xl" />
          ) : (
            <ClientSelector
              clients={allClients}
              selected={selected}
              onToggle={toggle}
              onSelectAll={selectAll}
              onClearAll={clearAll}
            />
          )}
          {activeClients.length === 0 && !clientsLoading && (
            <p className="text-xs text-slate-400 mt-2 text-center">
              No active clients. Add clients first to send reminders.
            </p>
          )}
        </div>

        {/* Step 2: Message type */}
        <div>
          <p className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-2">
            Step 2 — Reminder Type
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {REMINDER_TYPES.map(({ value, label }) => (
              <button
                key={value}
                onClick={() => handleTypeChange(value)}
                className={`py-2.5 px-3 rounded-xl text-xs font-semibold border transition-all ${
                  type === value
                    ? "bg-blue-700 text-white border-blue-700 shadow-sm"
                    : "bg-white text-slate-600 border-slate-200 hover:border-blue-300"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        {/* Step 2b: Deadline type (optional) */}
        <div>
          <p className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-2">
            Filing Deadline <span className="text-slate-400 font-normal normal-case">(optional)</span>
          </p>
          <div className="relative">
            <select
              value={deadlineType}
              onChange={(e) => setDeadlineType(e.target.value)}
              className="input-base appearance-none pr-8"
            >
              {DEADLINE_TYPE_OPTIONS.map(({ value, label }) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
            <ChevronDown size={16} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
          </div>
          <p className="text-xs text-slate-400 mt-1">
            When selected, the due date is included automatically and the deadline is marked as "reminded".
          </p>
        </div>

        {/* Step 3: Message */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs font-bold text-slate-500 uppercase tracking-wide">
              Step 3 — Message
            </p>
            <span className={`text-xs font-medium ${message.length > MAX_MSG * 0.9 ? "text-orange-600" : "text-slate-400"}`}>
              {message.length}/{MAX_MSG}
            </span>
          </div>
          <textarea
            value={message}
            onChange={(e) => setMessage(e.target.value.slice(0, MAX_MSG))}
            rows={4}
            placeholder="Type your message…"
            className="input-base resize-none"
          />
        </div>

        {/* Preview */}
        {selected.size > 0 && (
          <div className="bg-blue-50 border border-blue-200 rounded-2xl p-4">
            <p className="text-xs font-semibold text-blue-700 mb-1 flex items-center gap-1.5">
              <MessageSquare size={12} /> Preview
            </p>
            <p className="text-xs text-slate-600">{message || "—"}</p>
            <p className="text-xs text-blue-500 mt-2">
              Will be sent to {selected.size} client{selected.size !== 1 ? "s" : ""}
            </p>
          </div>
        )}

        {/* Send button */}
        <button
          onClick={handleSend}
          disabled={loading || selected.size === 0}
          className={`w-full flex items-center justify-center gap-2 py-3.5 rounded-2xl font-bold text-white text-base transition-all ${
            loading || selected.size === 0
              ? "bg-slate-400 cursor-not-allowed"
              : "bg-blue-700 hover:bg-blue-800 active:scale-[0.98]"
          }`}
        >
          {loading ? "Sending…" : (
            <>
              <Send size={18} />
              Send to {selected.size > 0 ? `${selected.size} Client${selected.size > 1 ? "s" : ""}` : "Selected Clients"}
            </>
          )}
        </button>
      </div>
    </div>
  );
}
