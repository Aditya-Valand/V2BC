"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import {
  CalendarClock, CheckCircle2, Send, RefreshCw, AlertCircle,
  Clock, Calendar, ChevronRight, Users, Zap,
} from "lucide-react";
import { toast } from "sonner";
import { isAfter, parseISO, differenceInDays } from "date-fns";
import { deadlinesApi } from "@/lib/api/deadlines";
import { remindersApi } from "@/lib/api/reminders";
import { clientsApi } from "@/lib/api/clients";
import { getApiError } from "@/lib/api/client";
import { DEADLINE_STATUS, DEADLINE_TYPES } from "@/constants";
import { formatDate, formatINR } from "@/lib/utils";

// ── Constants ─────────────────────────────────────────────────────────

const DAY_OPTIONS = [
  { value: 7,  label: "7 days"  },
  { value: 14, label: "14 days" },
  { value: 30, label: "30 days" },
  { value: 90, label: "3 months"},
];

// ── Urgency helper ────────────────────────────────────────────────────

function urgencyLabel(dueDateStr) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const due = parseISO(dueDateStr);
  const diff = differenceInDays(due, today);
  if (diff < 0)  return { label: `${Math.abs(diff)}d overdue`, cls: "bg-red-100 text-red-700"    };
  if (diff === 0) return { label: "Due today",                  cls: "bg-red-50 text-red-600"      };
  if (diff === 1) return { label: "Tomorrow",                   cls: "bg-orange-100 text-orange-700"};
  if (diff <= 7)  return { label: `${diff}d left`,              cls: "bg-yellow-100 text-yellow-700"};
  return           { label: `${diff}d left`,                    cls: "bg-slate-100 text-slate-600"  };
}

// ── Bulk Reminder Modal ───────────────────────────────────────────────

function BulkReminderModal({ deadline, onClose }) {
  const [message, setMessage] = useState(
    `This is a reminder for ${DEADLINE_TYPES[deadline?.deadline_type] || "filing"} due on ${formatDate(deadline?.due_date)}.`
  );
  const [loading, setLoading] = useState(false);
  const [result,  setResult]  = useState(null);

  const send = async () => {
    if (!message.trim()) { toast.error("Message cannot be empty."); return; }
    setLoading(true);
    try {
      const res = await remindersApi.sendBulk({
        client_ids: "all",
        message: message.trim(),
        type: "deadline",
        deadline_type: deadline?.deadline_type,
      });
      setResult(res.data.data);
    } catch (err) {
      toast.error(getApiError(err));
    } finally {
      setLoading(false);
    }
  };

  if (result) {
    return (
      <ModalShell onClose={onClose} title="Reminders Sent">
        <div className="py-2 space-y-3">
          <div className="grid grid-cols-3 gap-3 text-center">
            {[
              { label: "Sent",    value: result.sent,    color: "text-green-700 bg-green-50"  },
              { label: "Failed",  value: result.failed,  color: "text-red-700 bg-red-50"      },
              { label: "Skipped", value: result.skipped, color: "text-slate-600 bg-slate-100" },
            ].map(({ label, value, color }) => (
              <div key={label} className={`rounded-xl p-3 ${color}`}>
                <p className="text-2xl font-bold">{value}</p>
                <p className="text-xs opacity-70">{label}</p>
              </div>
            ))}
          </div>
          {result.details?.length > 0 && (
            <div className="bg-slate-50 rounded-xl max-h-40 overflow-y-auto divide-y divide-slate-200">
              {result.details.map((d) => (
                <div key={d.client_id} className="px-3 py-2 flex items-center justify-between">
                  <span className="text-xs text-slate-700 font-medium">{d.client_name}</span>
                  <span className={`text-[11px] font-semibold ${
                    d.status === "delivered" ? "text-green-600" : "text-slate-400"
                  }`}>{d.status}</span>
                </div>
              ))}
            </div>
          )}
          <button onClick={onClose} className="btn-primary w-full">Done</button>
        </div>
      </ModalShell>
    );
  }

  return (
    <ModalShell onClose={onClose} title="Send Bulk Reminder" subtitle={`For: ${DEADLINE_TYPES[deadline?.deadline_type] || "Deadline"} · ${formatDate(deadline?.due_date)}`}>
      <div className="space-y-4">
        <div>
          <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">
            Message <span className="text-slate-400 font-normal normal-case">({message.length}/500)</span>
          </label>
          <textarea
            value={message}
            onChange={(e) => setMessage(e.target.value.slice(0, 500))}
            rows={4}
            className="input-base resize-none"
          />
        </div>
        <div className="flex gap-3">
          <button onClick={onClose}  className="btn-outline flex-1">Cancel</button>
          <button onClick={send} disabled={loading} className="btn-primary flex-1">
            {loading ? "Sending…" : <><Send size={14} /> Send to All</>}
          </button>
        </div>
      </div>
    </ModalShell>
  );
}

// ── Complete Modal ────────────────────────────────────────────────────

function CompleteModal({ deadline, onClose, onDone }) {
  const [notes,   setNotes]   = useState("");
  const [loading, setLoading] = useState(false);

  const complete = async () => {
    setLoading(true);
    try {
      await deadlinesApi.complete(deadline.id, notes.trim() || null);
      toast.success("Marked as filed.");
      onDone();
    } catch (err) {
      toast.error(getApiError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <ModalShell
      onClose={onClose}
      title="Mark as Filed"
      subtitle={`${deadline.description} · Due ${formatDate(deadline.due_date)}`}
    >
      <div className="space-y-4">
        <div>
          <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">
            Notes <span className="text-slate-400 font-normal normal-case">(optional)</span>
          </label>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="e.g. Filed via GST portal on 28-Feb"
            rows={2}
            className="input-base resize-none"
          />
        </div>
        <div className="flex gap-3">
          <button onClick={onClose} className="btn-outline flex-1">Cancel</button>
          <button onClick={complete} disabled={loading} className="btn-primary flex-1">
            {loading ? "Saving…" : <><CheckCircle2 size={14} /> Confirm Filed</>}
          </button>
        </div>
      </div>
    </ModalShell>
  );
}

function ModalShell({ title, subtitle, onClose, children }) {
  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/40 backdrop-blur-sm">
      <div className="bg-white w-full sm:max-w-md sm:rounded-2xl rounded-t-2xl p-6 shadow-2xl">
        <div className="mb-4">
          <h2 className="text-base font-bold text-slate-800">{title}</h2>
          {subtitle && <p className="text-xs text-slate-400 mt-0.5">{subtitle}</p>}
        </div>
        {children}
      </div>
    </div>
  );
}

// ── Deadline Row ──────────────────────────────────────────────────────

function DeadlineRow({ d, onComplete, onRemind }) {
  const urgency = urgencyLabel(d.due_date);
  const s = DEADLINE_STATUS[d.status] || DEADLINE_STATUS.pending;
  const canComplete = ["pending", "reminded", "acknowledged"].includes(d.status);

  return (
    <div className="px-4 py-3.5 flex items-start gap-3">
      {/* Urgency dot */}
      <div className={`w-2 h-2 rounded-full mt-1.5 shrink-0 ${
        urgency.cls.includes("red")    ? "bg-red-500" :
        urgency.cls.includes("orange") ? "bg-orange-400" :
        urgency.cls.includes("yellow") ? "bg-yellow-400" : "bg-slate-300"
      }`} />

      {/* Main info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <p className="text-sm font-semibold text-slate-800 truncate">
            {DEADLINE_TYPES[d.deadline_type] || d.deadline_type}
          </p>
          <span className={`text-[11px] font-semibold px-1.5 py-0.5 rounded-full ${urgency.cls}`}>
            {urgency.label}
          </span>
        </div>
        {d.client_name && (
          <Link href={`/clients/${d.client_id || d.business_id}`} className="text-xs text-blue-600 hover:underline font-medium">
            {d.client_name}
          </Link>
        )}
        <p className="text-xs text-slate-400 mt-0.5">
          Due: {formatDate(d.due_date)}
          {d.description && ` · ${d.description}`}
        </p>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-1.5 shrink-0">
        <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-full ${s.bg} ${s.text}`}>
          {s.label}
        </span>
        {canComplete && (
          <button
            onClick={() => onComplete(d)}
            title="Mark as filed"
            className="w-7 h-7 flex items-center justify-center rounded-lg bg-green-50 hover:bg-green-100 text-green-600 transition-colors"
          >
            <CheckCircle2 size={14} />
          </button>
        )}
        <button
          onClick={() => onRemind(d)}
          title="Send reminder"
          className="w-7 h-7 flex items-center justify-center rounded-lg bg-blue-50 hover:bg-blue-100 text-blue-600 transition-colors"
        >
          <Send size={13} />
        </button>
      </div>
    </div>
  );
}

// ── Section wrapper ───────────────────────────────────────────────────

function DeadlineSection({ title, icon: Icon, iconCls, items, onComplete, onRemind, defaultOpen = true }) {
  const [open, setOpen] = useState(defaultOpen);
  if (!items?.length) return null;

  return (
    <div>
      <button
        onClick={() => setOpen((v) => !v)}
        className={`flex items-center gap-2 mb-2 w-full text-left`}
      >
        <Icon size={15} className={iconCls} />
        <span className="text-sm font-bold text-slate-700">{title}</span>
        <span className="text-xs text-slate-400 ml-1">{items.length}</span>
        <ChevronRight size={14} className={`ml-auto text-slate-400 transition-transform ${open ? "rotate-90" : ""}`} />
      </button>
      {open && (
        <div className="bg-white rounded-2xl border border-slate-200 divide-y divide-slate-100 overflow-hidden">
          {items.map((d) => (
            <DeadlineRow key={d.id} d={d} onComplete={onComplete} onRemind={onRemind} />
          ))}
        </div>
      )}
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────

export default function DeadlinesPage() {
  const qc = useQueryClient();
  const [days,           setDays]           = useState(30);
  const [completeTarget, setCompleteTarget] = useState(null);
  const [remindTarget,   setRemindTarget]   = useState(null);

  const { data, isLoading, refetch, isFetching } = useQuery({
    queryKey: ["upcoming-deadlines", days],
    queryFn: () => deadlinesApi.upcoming(days).then((r) => r.data.data),
  });

  const summary  = data?.summary  || {};
  const overdue  = data?.overdue  || [];
  const thisWeek = data?.this_week || [];
  const nextWeek = data?.next_week || [];
  const later    = data?.later    || [];

  return (
    <div className="max-w-3xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-xl font-bold text-slate-800">Deadlines</h1>
          <p className="text-sm text-slate-400 mt-0.5">Upcoming filings across all clients</p>
        </div>
        <button
          onClick={() => refetch()}
          disabled={isFetching}
          className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-blue-700 transition-colors"
        >
          <RefreshCw size={14} className={isFetching ? "animate-spin" : ""} />
          <span className="hidden sm:inline">Refresh</span>
        </button>
      </div>

      {/* Days filter */}
      <div className="flex gap-2 mb-5">
        {DAY_OPTIONS.map(({ value, label }) => (
          <button
            key={value}
            onClick={() => setDays(value)}
            className={`text-xs font-semibold px-3.5 py-1.5 rounded-full border transition-colors ${
              days === value
                ? "bg-blue-700 text-white border-blue-700"
                : "bg-white text-slate-600 border-slate-200 hover:border-blue-300"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Summary stats */}
      {!isLoading && (
        <div className="grid grid-cols-4 gap-3 mb-6">
          {[
            { label: "Total",      value: summary.total_upcoming ?? 0, cls: "bg-slate-100 text-slate-700" },
            { label: "Overdue",    value: summary.overdue ?? 0,        cls: summary.overdue > 0 ? "bg-red-50 text-red-700" : "bg-slate-100 text-slate-600" },
            { label: "This Week",  value: summary.this_week ?? 0,      cls: "bg-yellow-50 text-yellow-700" },
            { label: "Clients",    value: summary.unique_clients ?? 0, cls: "bg-blue-50 text-blue-700" },
          ].map(({ label, value, cls }) => (
            <div key={label} className={`rounded-2xl p-3 text-center ${cls}`}>
              <p className="text-2xl font-bold">{value}</p>
              <p className="text-xs opacity-70 mt-0.5">{label}</p>
            </div>
          ))}
        </div>
      )}

      {/* Deadline sections */}
      {isLoading ? (
        <div className="space-y-3">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="h-16 bg-slate-200 animate-pulse rounded-xl" />
          ))}
        </div>
      ) : (overdue.length + thisWeek.length + nextWeek.length + later.length) === 0 ? (
        <div className="bg-green-50 border border-green-200 rounded-2xl p-12 text-center">
          <CalendarClock size={40} className="text-green-400 mx-auto mb-3" />
          <p className="text-base font-bold text-green-800">No deadlines in this window</p>
          <p className="text-sm text-green-600 mt-1">All filings are up to date.</p>
        </div>
      ) : (
        <div className="space-y-5">
          <DeadlineSection
            title="Overdue"
            icon={AlertCircle}
            iconCls="text-red-500"
            items={overdue}
            onComplete={setCompleteTarget}
            onRemind={setRemindTarget}
            defaultOpen
          />
          <DeadlineSection
            title="This Week"
            icon={Zap}
            iconCls="text-yellow-500"
            items={thisWeek}
            onComplete={setCompleteTarget}
            onRemind={setRemindTarget}
            defaultOpen
          />
          <DeadlineSection
            title="Next Week"
            icon={Clock}
            iconCls="text-blue-500"
            items={nextWeek}
            onComplete={setCompleteTarget}
            onRemind={setRemindTarget}
            defaultOpen={false}
          />
          <DeadlineSection
            title="Later"
            icon={Calendar}
            iconCls="text-slate-400"
            items={later}
            onComplete={setCompleteTarget}
            onRemind={setRemindTarget}
            defaultOpen={false}
          />
        </div>
      )}

      {/* Modals */}
      {completeTarget && (
        <CompleteModal
          deadline={completeTarget}
          onClose={() => setCompleteTarget(null)}
          onDone={() => {
            setCompleteTarget(null);
            qc.invalidateQueries({ queryKey: ["upcoming-deadlines"] });
          }}
        />
      )}
      {remindTarget && (
        <BulkReminderModal
          deadline={remindTarget}
          onClose={() => setRemindTarget(null)}
        />
      )}
    </div>
  );
}
