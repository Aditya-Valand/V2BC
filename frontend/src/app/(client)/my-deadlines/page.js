"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  CalendarClock, CheckCircle2, Clock, AlertCircle,
  Check, ChevronDown, ChevronUp,
} from "lucide-react";
import { toast } from "sonner";
import { differenceInDays, parseISO } from "date-fns";
import { deadlinesApi } from "@/lib/api/deadlines";
import { getApiError } from "@/lib/api/client";
import { DEADLINE_STATUS, DEADLINE_TYPES } from "@/constants";
import { formatDate } from "@/lib/utils";
import useAuthStore from "@/store/authStore";

// ── Helpers ───────────────────────────────────────────────────────────

function getUrgency(dueDateStr, status) {
  if (status === "completed") return { label: "Completed", cls: "text-green-700 bg-green-100", days: null };
  if (status === "missed")    return { label: "Missed",    cls: "text-red-700 bg-red-100",     days: null };

  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const due  = parseISO(dueDateStr);
  const diff = differenceInDays(due, today);

  if (diff < 0)   return { label: `${Math.abs(diff)}d overdue`, cls: "text-red-700 bg-red-100",      days: diff };
  if (diff === 0) return { label: "Due today",                   cls: "text-red-600 bg-red-50",       days: 0    };
  if (diff === 1) return { label: "Tomorrow",                    cls: "text-orange-700 bg-orange-100", days: 1   };
  if (diff <= 7)  return { label: `${diff} days left`,           cls: "text-yellow-700 bg-yellow-100", days: diff };
  return           { label: `${diff} days left`,                 cls: "text-slate-600 bg-slate-100",  days: diff };
}

// ── Deadline Card ─────────────────────────────────────────────────────

function DeadlineCard({ d, onAcknowledge, ackLoading }) {
  const [expanded, setExpanded] = useState(false);
  const urgency    = getUrgency(d.due_date, d.status);
  const s          = DEADLINE_STATUS[d.status] || DEADLINE_STATUS.pending;
  const canAck     = d.status === "pending" || d.status === "reminded";
  const isOverdue  = urgency.days !== null && urgency.days < 0;
  const isDone     = d.status === "completed" || d.status === "missed";

  return (
    <div className={`bg-white rounded-2xl border overflow-hidden transition-all ${
      isOverdue ? "border-red-200" : isDone ? "border-green-200" : "border-slate-200"
    }`}>
      {/* Top stripe */}
      <div className={`h-1 ${
        isOverdue ? "bg-red-400" :
        urgency.days === 0 ? "bg-orange-400" :
        urgency.days !== null && urgency.days <= 7 ? "bg-yellow-400" :
        isDone ? "bg-green-400" : "bg-blue-300"
      }`} />

      {/* Main content */}
      <div className="px-4 py-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            {/* Filing type */}
            <p className="text-sm font-bold text-slate-800 leading-tight">
              {DEADLINE_TYPES[d.deadline_type] || d.deadline_type}
            </p>
            {d.description && d.description !== DEADLINE_TYPES[d.deadline_type] && (
              <p className="text-xs text-slate-500 mt-0.5 truncate">{d.description}</p>
            )}
            {/* Due date */}
            <p className="text-xs text-slate-400 mt-1.5">
              Due: <span className="font-semibold text-slate-600">{formatDate(d.due_date)}</span>
            </p>
          </div>

          {/* Urgency badge */}
          <span className={`shrink-0 text-[11px] font-bold px-2.5 py-1 rounded-full ${urgency.cls}`}>
            {urgency.label}
          </span>
        </div>

        {/* Status + actions row */}
        <div className="flex items-center justify-between mt-3 pt-3 border-t border-slate-100">
          <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${s.bg} ${s.text}`}>
            {s.label}
          </span>

          <div className="flex items-center gap-2">
            {/* Expand/collapse for details */}
            <button
              onClick={() => setExpanded((v) => !v)}
              className="text-xs text-slate-400 hover:text-slate-600 flex items-center gap-0.5"
            >
              Details {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            </button>

            {/* Acknowledge button */}
            {canAck && (
              <button
                onClick={() => onAcknowledge(d.id)}
                disabled={ackLoading}
                className="flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 bg-blue-700 text-white rounded-lg hover:bg-blue-800 active:scale-[0.97] transition-all"
              >
                <Check size={12} strokeWidth={3} />
                Acknowledge
              </button>
            )}

            {isDone && (
              <span className="flex items-center gap-1 text-xs text-green-600 font-medium">
                <CheckCircle2 size={14} /> Done
              </span>
            )}
          </div>
        </div>

        {/* Expanded details */}
        {expanded && (
          <div className="mt-3 pt-3 border-t border-slate-100 space-y-1.5 text-xs text-slate-500">
            {d.period_start && (
              <div className="flex justify-between">
                <span>Filing Period</span>
                <span className="font-medium text-slate-700">
                  {formatDate(d.period_start, "d MMM")} – {formatDate(d.period_end, "d MMM yyyy")}
                </span>
              </div>
            )}
            {d.reminder_sent_at && (
              <div className="flex justify-between">
                <span>Reminded on</span>
                <span className="font-medium text-slate-700">{formatDate(d.reminder_sent_at, "d MMM yyyy")}</span>
              </div>
            )}
            {d.acknowledged_at && (
              <div className="flex justify-between">
                <span>Acknowledged</span>
                <span className="font-medium text-slate-700">{formatDate(d.acknowledged_at, "d MMM yyyy")}</span>
              </div>
            )}
            {d.completed_at && (
              <div className="flex justify-between">
                <span>Completed</span>
                <span className="font-medium text-slate-700">{formatDate(d.completed_at, "d MMM yyyy")}</span>
              </div>
            )}
            {d.notes && (
              <div className="mt-2 bg-slate-50 rounded-lg px-3 py-2 text-slate-600">{d.notes}</div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Empty state ───────────────────────────────────────────────────────

function EmptyState({ filter }) {
  const msgs = {
    all:          { title: "No deadlines yet",       sub: "Your CA will set up filing deadlines for you." },
    pending:      { title: "No pending deadlines",   sub: "You're all caught up!" },
    completed:    { title: "No completed filings",   sub: "Mark deadlines as acknowledged to track progress." },
  };
  const { title, sub } = msgs[filter] || msgs.all;
  return (
    <div className="bg-white rounded-2xl border border-slate-200 py-14 text-center">
      <CalendarClock size={36} className="mx-auto text-slate-300 mb-3" />
      <p className="text-sm font-semibold text-slate-500">{title}</p>
      <p className="text-xs text-slate-400 mt-1">{sub}</p>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────

export default function ClientDeadlinesPage() {
  const qc = useQueryClient();
  const [filter, setFilter] = useState("all");
  const orgId = useAuthStore((s) => s.getOrgId());   // for client, org.id = business_id

  const { data, isLoading } = useQuery({
    queryKey: ["my-deadlines", orgId],
    queryFn: () => deadlinesApi.forClient(orgId).then((r) => r.data.data),
    enabled: !!orgId,
  });

  const acknowledgeMutation = useMutation({
    mutationFn: (id) => deadlinesApi.acknowledge(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["my-deadlines", orgId] });
      toast.success("Deadline acknowledged. Your CA has been notified.");
    },
    onError: (err) => toast.error(getApiError(err)),
  });

  const deadlines = data?.deadlines || [];
  const summary   = data?.summary   || {};

  // Filter
  const filtered = filter === "all"
    ? deadlines
    : filter === "pending"
    ? deadlines.filter((d) => ["pending", "reminded", "acknowledged"].includes(d.status))
    : deadlines.filter((d) => ["completed", "missed"].includes(d.status));

  // Sort: overdue first, then by due_date asc
  const sorted = [...filtered].sort((a, b) => {
    const da = parseISO(a.due_date);
    const db = parseISO(b.due_date);
    const today = new Date();
    const aOver = da < today;
    const bOver = db < today;
    if (aOver && !bOver) return -1;
    if (!aOver && bOver) return 1;
    return da - db;
  });

  return (
    <div className="p-4 space-y-4">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-slate-800">Deadlines</h1>
        <p className="text-sm text-slate-400 mt-0.5">Your upcoming filing dates</p>
      </div>

      {/* Summary bar */}
      {!isLoading && summary.total > 0 && (
        <div className="grid grid-cols-3 gap-2">
          {[
            { label: "Pending",  value: (summary.pending  || 0) + (summary.reminded || 0) + (summary.acknowledged || 0), cls: "bg-blue-50 text-blue-700"   },
            { label: "Overdue",  value: summary.overdue  || 0, cls: summary.overdue > 0 ? "bg-red-50 text-red-700" : "bg-slate-100 text-slate-600" },
            { label: "Done",     value: summary.completed || 0, cls: "bg-green-50 text-green-700" },
          ].map(({ label, value, cls }) => (
            <div key={label} className={`rounded-2xl p-3 text-center ${cls}`}>
              <p className="text-2xl font-bold">{value}</p>
              <p className="text-xs opacity-70 mt-0.5">{label}</p>
            </div>
          ))}
        </div>
      )}

      {/* Filter tabs */}
      <div className="flex bg-slate-100 rounded-xl p-1 gap-1">
        {[
          { key: "all",       label: "All"       },
          { key: "pending",   label: "Pending"   },
          { key: "completed", label: "Completed" },
        ].map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setFilter(key)}
            className={`flex-1 py-1.5 text-xs font-semibold rounded-lg transition-all ${
              filter === key ? "bg-white text-blue-700 shadow-sm" : "text-slate-500"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="space-y-3">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-28 bg-slate-200 animate-pulse rounded-2xl" />
          ))}
        </div>
      ) : sorted.length === 0 ? (
        <EmptyState filter={filter} />
      ) : (
        <div className="space-y-3">
          {sorted.map((d) => (
            <DeadlineCard
              key={d.id}
              d={d}
              onAcknowledge={(id) => acknowledgeMutation.mutate(id)}
              ackLoading={acknowledgeMutation.isPending}
            />
          ))}
        </div>
      )}

      {/* Informational footer */}
      {!isLoading && sorted.length > 0 && (
        <p className="text-xs text-slate-400 text-center pb-2">
          Acknowledging a deadline lets your CA know you're aware of it.
        </p>
      )}
    </div>
  );
}
