"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft, TrendingUp, TrendingDown, Minus, Activity,
  CalendarClock, AlertTriangle, Copy, Check, RefreshCw,
  CheckCircle2, Clock, FileText, Send, Download, ChevronRight,
  Building2, Phone, MapPin, Hash, MessageCircle, ChevronDown,
} from "lucide-react";
import { toast } from "sonner";
import { format } from "date-fns";
import { clientsApi } from "@/lib/api/clients";
import { deadlinesApi } from "@/lib/api/deadlines";
import { validationApi } from "@/lib/api/validation";
import { whatsappApi } from "@/lib/api/whatsapp";
import { getApiError } from "@/lib/api/client";
import { COMPLIANCE_COLORS, DEADLINE_STATUS, DEADLINE_TYPES, ALERT_SEVERITY } from "@/constants";
import { formatINR, formatDate, timeAgo, getInitials, downloadBlob } from "@/lib/utils";

// ── Sub-components ────────────────────────────────────────────────────

function StatCard({ label, value, icon: Icon, color }) {
  const colors = {
    green:  "bg-green-50 text-green-700",
    red:    "bg-red-50 text-red-700",
    blue:   "bg-blue-50 text-blue-700",
    slate:  "bg-slate-100 text-slate-700",
  };
  return (
    <div className={`rounded-2xl p-4 ${colors[color] || colors.slate}`}>
      <div className="flex items-center justify-between mb-2">
        <p className="text-xs font-medium opacity-70">{label}</p>
        <Icon size={16} className="opacity-50" />
      </div>
      <p className="text-xl font-bold">{value}</p>
    </div>
  );
}

function EvidenceBar({ stats }) {
  if (!stats) return null;
  const total = stats.transaction_count || 0;
  if (total === 0) return null;
  const withEvidence = stats.with_evidence || 0;
  const pct = Math.round((withEvidence / total) * 100);
  const eb = stats.evidence_breakdown || {};
  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-4">
      <div className="flex items-center justify-between mb-3">
        <p className="text-sm font-semibold text-slate-700">Evidence Health</p>
        <span className="text-sm font-bold text-slate-800">{pct}%</span>
      </div>
      <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${
            pct >= 70 ? "bg-green-500" : pct >= 40 ? "bg-yellow-400" : "bg-red-500"
          }`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="flex gap-4 mt-3 text-xs text-slate-500">
        <span><span className="font-semibold text-green-700">{eb.strong || 0}</span> Strong</span>
        <span><span className="font-semibold text-yellow-700">{eb.medium || 0}</span> Medium</span>
        <span><span className="font-semibold text-red-700">{eb.weak || 0}</span> Weak</span>
        <span><span className="font-semibold text-slate-500">{stats.without_evidence || 0}</span> None</span>
      </div>
    </div>
  );
}

function RecentTxRow({ tx }) {
  const isIncome = tx.type === "sale";
  return (
    <div className="flex items-center gap-3 px-4 py-3">
      <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
        isIncome ? "bg-green-100" : "bg-red-100"
      }`}>
        {isIncome
          ? <TrendingUp size={14} className="text-green-600" />
          : <TrendingDown size={14} className="text-red-600" />}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-slate-700 truncate">
          {tx.description || tx.category || (isIncome ? "Sale" : "Expense")}
        </p>
        <p className="text-xs text-slate-400">{formatDate(tx.transaction_date)}</p>
      </div>
      <span className={`text-sm font-semibold shrink-0 ${isIncome ? "text-green-700" : "text-red-700"}`}>
        {isIncome ? "+" : "−"}{formatINR(tx.amount)}
      </span>
    </div>
  );
}

// ── Tabs ──────────────────────────────────────────────────────────────

function OverviewTab({ detail, clientId }) {
  const qc = useQueryClient();
  const [exportLoading, setExportLoading] = useState(false);
  const month = format(new Date(), "yyyy-MM");

  const { stats, recent_transactions: txns = [], compliance_score, compliance_color } = detail;
  const c = COMPLIANCE_COLORS[compliance_color] || COMPLIANCE_COLORS.green;

  const handleExport = async () => {
    setExportLoading(true);
    try {
      const res = await clientsApi.exportFiling(clientId, month);
      downloadBlob(res.data, `filing-summary-${clientId}-${month}.xlsx`);
      toast.success("Export downloaded.");
    } catch (err) {
      toast.error(getApiError(err));
    } finally {
      setExportLoading(false);
    }
  };

  return (
    <div className="space-y-5">
      {/* Stats */}
      <div className="grid grid-cols-2 gap-3">
        <StatCard label="Sales (This Month)"    value={formatINR(stats?.total_sales_this_month)}    icon={TrendingUp}    color="green" />
        <StatCard label="Expenses (This Month)"  value={formatINR(stats?.total_expenses_this_month)} icon={TrendingDown}  color="red"   />
        <StatCard label="Net Income"             value={formatINR(stats?.net_income_this_month)}     icon={Activity}      color="blue"  />
        <StatCard label="Transactions"           value={stats?.transaction_count ?? 0}               icon={Minus}         color="slate" />
      </div>

      {/* Compliance score */}
      {compliance_score != null && (
        <div className="bg-white rounded-2xl border border-slate-200 p-4 flex items-center gap-4">
          <div className={`w-14 h-14 rounded-full flex items-center justify-center ${c.bg}`}>
            <span className={`text-lg font-bold ${c.text}`}>{Math.round(compliance_score)}</span>
          </div>
          <div>
            <p className="text-sm font-semibold text-slate-700">Compliance Score</p>
            <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${c.bg} ${c.text}`}>{c.label}</span>
          </div>
        </div>
      )}

      {/* Evidence health */}
      <EvidenceBar stats={stats} />

      {/* Action buttons */}
      <div className="grid grid-cols-2 gap-3">
        <button
          onClick={handleExport}
          disabled={exportLoading}
          className="btn-outline flex items-center justify-center gap-2 text-sm"
        >
          <Download size={15} />
          {exportLoading ? "Exporting…" : "Export Filing"}
        </button>
      </div>

      {/* Recent transactions */}
      {txns.length > 0 && (
        <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
          <p className="px-4 py-3 text-sm font-semibold text-slate-700 border-b border-slate-100">
            Recent Transactions
          </p>
          <div className="divide-y divide-slate-100">
            {txns.slice(0, 8).map((tx) => <RecentTxRow key={tx.id} tx={tx} />)}
          </div>
        </div>
      )}
    </div>
  );
}

function DeadlinesTab({ clientId }) {
  const qc = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["client-deadlines", clientId],
    queryFn: () => deadlinesApi.forClient(clientId).then((r) => r.data.data),
  });

  const completeMutation = useMutation({
    mutationFn: (id) => deadlinesApi.complete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["client-deadlines", clientId] });
      toast.success("Deadline marked as filed.");
    },
    onError: (err) => toast.error(getApiError(err)),
  });

  const generateMutation = useMutation({
    mutationFn: () => deadlinesApi.generate(clientId),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ["client-deadlines", clientId] });
      toast.success(res.data.data?.message || "Deadlines generated.");
    },
    onError: (err) => toast.error(getApiError(err)),
  });

  if (isLoading) return (
    <div className="space-y-3">
      {[...Array(4)].map((_, i) => (
        <div key={i} className="h-16 bg-slate-100 rounded-xl animate-pulse" />
      ))}
    </div>
  );

  const deadlines = data?.deadlines || [];
  const summary   = data?.summary   || {};

  return (
    <div className="space-y-4">
      {/* Summary pills */}
      <div className="flex gap-2 flex-wrap">
        {[
          { label: "Pending",  value: summary.pending,  color: "bg-gray-100 text-gray-700"   },
          { label: "Overdue",  value: summary.overdue,  color: "bg-red-100 text-red-700"     },
          { label: "Done",     value: summary.completed, color: "bg-green-100 text-green-700" },
        ].map(({ label, value, color }) => value > 0 && (
          <span key={label} className={`text-xs font-medium px-2.5 py-1 rounded-full ${color}`}>
            {value} {label}
          </span>
        ))}
        <button
          onClick={() => generateMutation.mutate()}
          disabled={generateMutation.isPending}
          className="ml-auto text-xs text-blue-700 font-medium flex items-center gap-1 hover:underline"
        >
          <RefreshCw size={12} className={generateMutation.isPending ? "animate-spin" : ""} />
          Generate
        </button>
      </div>

      {/* Deadline list */}
      {deadlines.length === 0 ? (
        <div className="text-center py-10 text-slate-400">
          <CalendarClock size={32} className="mx-auto mb-2" />
          <p className="text-sm">No deadlines found. Click Generate.</p>
        </div>
      ) : (
        <div className="bg-white rounded-2xl border border-slate-200 divide-y divide-slate-100 overflow-hidden">
          {deadlines.map((d) => {
            const s = DEADLINE_STATUS[d.status] || DEADLINE_STATUS.pending;
            const isPending = ["pending", "reminded", "acknowledged"].includes(d.status);
            return (
              <div key={d.id} className="px-4 py-3 flex items-center justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-700 truncate">{d.description}</p>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Due: <span className="font-medium">{formatDate(d.due_date)}</span>
                    {" · "}{DEADLINE_TYPES[d.deadline_type] || d.deadline_type}
                  </p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <span className={`text-[11px] font-medium px-2 py-0.5 rounded-full ${s.bg} ${s.text}`}>
                    {s.label}
                  </span>
                  {isPending && (
                    <button
                      onClick={() => completeMutation.mutate(d.id)}
                      disabled={completeMutation.isPending}
                      title="Mark as filed"
                      className="w-7 h-7 flex items-center justify-center rounded-lg bg-green-50 hover:bg-green-100 text-green-600 transition-colors"
                    >
                      <CheckCircle2 size={15} />
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function AnomaliesTab({ clientId }) {
  const { data, isLoading } = useQuery({
    queryKey: ["client-anomalies", clientId],
    queryFn: () => validationApi.anomalies(clientId).then((r) => r.data.data),
  });

  if (isLoading) return (
    <div className="space-y-3">
      {[...Array(3)].map((_, i) => (
        <div key={i} className="h-20 bg-slate-100 rounded-xl animate-pulse" />
      ))}
    </div>
  );

  if (!data) return null;

  const gapColors = {
    ok:       "text-green-700 bg-green-50",
    warning:  "text-yellow-700 bg-yellow-50",
    critical: "text-red-700 bg-red-50",
  };

  return (
    <div className="space-y-4">
      {/* Gap status */}
      <div className="bg-white rounded-2xl border border-slate-200 p-4">
        <p className="text-sm font-semibold text-slate-700 mb-3">Entry Gap Analysis</p>
        <div className="flex items-center gap-3">
          <div className={`px-3 py-1 rounded-full text-xs font-semibold ${gapColors[data.gap_status] || gapColors.ok}`}>
            {data.gap_days} day{data.gap_days !== 1 ? "s" : ""} gap · {data.gap_status?.toUpperCase()}
          </div>
        </div>
      </div>

      {/* Summary stats */}
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-white rounded-2xl border border-slate-200 p-4">
          <p className="text-xs text-slate-400 mb-1">Outliers (30d)</p>
          <p className={`text-2xl font-bold ${data.outlier_count_30d > 0 ? "text-orange-600" : "text-slate-700"}`}>
            {data.outlier_count_30d ?? 0}
          </p>
        </div>
        <div className="bg-white rounded-2xl border border-slate-200 p-4">
          <p className="text-xs text-slate-400 mb-1">Duplicates (30d)</p>
          <p className={`text-2xl font-bold ${data.duplicate_count_30d > 0 ? "text-orange-600" : "text-slate-700"}`}>
            {data.duplicate_count_30d ?? 0}
          </p>
        </div>
      </div>

      {/* Averages */}
      {data.averages && (
        <div className="bg-white rounded-2xl border border-slate-200 p-4 space-y-2">
          <p className="text-sm font-semibold text-slate-700 mb-2">30-Day Averages</p>
          <div className="flex justify-between text-sm">
            <span className="text-slate-500">Avg. Sale</span>
            <span className="font-semibold text-green-700">{formatINR(data.averages.sale_avg_30d)}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-slate-500">Avg. Expense</span>
            <span className="font-semibold text-red-700">{formatINR(data.averages.expense_avg_30d)}</span>
          </div>
        </div>
      )}

      {/* Flagged transactions */}
      {data.flagged_transactions?.length > 0 && (
        <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
          <p className="px-4 py-3 text-sm font-semibold text-slate-700 border-b border-slate-100 flex items-center gap-2">
            <AlertTriangle size={14} className="text-orange-500" />
            Flagged Transactions
          </p>
          <div className="divide-y divide-slate-100">
            {data.flagged_transactions.map((tx) => (
              <div key={tx.id} className="px-4 py-3">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="text-sm font-medium text-slate-700">{formatINR(tx.amount)}</p>
                    <p className="text-xs text-slate-400">{formatDate(tx.transaction_date)} · {tx.type}</p>
                  </div>
                  {tx.flag_reason && (
                    <span className="text-[11px] text-orange-700 bg-orange-50 px-2 py-0.5 rounded-full">
                      {tx.flag_reason}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function WhatsAppTab({ clientId }) {
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState("");

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ["wa-messages", clientId, page, status],
    queryFn: () =>
      whatsappApi.messages(clientId, { page, per_page: 20, ...(status ? { status } : {}) })
        .then((r) => r.data.data),
    keepPreviousData: true,
  });

  const messages = data?.messages || [];
  const total = data?.total || 0;
  const pages = Math.ceil(total / 20);

  const STATUS_MAP = {
    received:          { label: "Received",          cls: "bg-blue-100 text-blue-700"    },
    parsed:            { label: "Parsed",             cls: "bg-green-100 text-green-700"  },
    statement_created: { label: "Logged",             cls: "bg-emerald-100 text-emerald-700" },
    parse_failed:      { label: "Parse Failed",       cls: "bg-red-100 text-red-700"      },
  };

  const statusFilters = [
    { value: "",                  label: "All" },
    { value: "received",          label: "Received" },
    { value: "parsed",            label: "Parsed" },
    { value: "statement_created", label: "Logged" },
    { value: "parse_failed",      label: "Failed" },
  ];

  if (isLoading) return (
    <div className="space-y-2">
      {[...Array(5)].map((_, i) => (
        <div key={i} className="h-16 bg-slate-100 rounded-xl animate-pulse" />
      ))}
    </div>
  );

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex gap-2 flex-wrap">
        {statusFilters.map(({ value, label }) => (
          <button
            key={value}
            onClick={() => { setStatus(value); setPage(1); }}
            className={`text-xs font-semibold px-3 py-1.5 rounded-full border transition-all ${
              status === value
                ? "bg-blue-700 text-white border-blue-700"
                : "bg-white text-slate-600 border-slate-200 hover:border-blue-300"
            }`}
          >
            {label}
          </button>
        ))}
        {isFetching && <span className="text-xs text-slate-400 self-center">Loading…</span>}
      </div>

      {/* Count */}
      {total > 0 && (
        <p className="text-xs text-slate-400">{total} message{total !== 1 ? "s" : ""}</p>
      )}

      {/* Messages list */}
      {messages.length === 0 ? (
        <div className="text-center py-12">
          <MessageCircle size={36} className="mx-auto mb-3 text-slate-300" />
          <p className="text-sm text-slate-500 font-medium">No WhatsApp messages yet</p>
          <p className="text-xs text-slate-400 mt-1">
            Messages sent via WhatsApp will appear here once the webhook is active.
          </p>
        </div>
      ) : (
        <div className="bg-white rounded-2xl border border-slate-200 divide-y divide-slate-100 overflow-hidden">
          {messages.map((msg) => {
            const s = STATUS_MAP[msg.status] || STATUS_MAP.received;
            const isIncoming = msg.direction !== "outbound";
            return (
              <div key={msg.id} className="px-4 py-3">
                <div className="flex items-start justify-between gap-3">
                  {/* Message bubble */}
                  <div className={`flex-1 min-w-0 text-sm rounded-xl px-3 py-2 ${
                    isIncoming ? "bg-slate-50 text-slate-700" : "bg-blue-50 text-blue-900"
                  }`}>
                    <p className="break-words leading-relaxed">{msg.body || msg.content || "—"}</p>
                    {msg.parsed_amount != null && (
                      <p className="text-xs mt-1.5 font-semibold text-green-700">
                        ₹{msg.parsed_amount.toLocaleString("en-IN")}
                        {msg.parsed_type && ` · ${msg.parsed_type}`}
                      </p>
                    )}
                  </div>
                  {/* Meta */}
                  <div className="shrink-0 text-right space-y-1">
                    <span className={`inline-block text-[10px] font-semibold px-2 py-0.5 rounded-full ${s.cls}`}>
                      {s.label}
                    </span>
                    <p className="text-[10px] text-slate-400">
                      {msg.received_at
                        ? new Date(msg.received_at).toLocaleDateString("en-IN", {
                            day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit"
                          })
                        : "—"}
                    </p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Pagination */}
      {pages > 1 && (
        <div className="flex items-center justify-between pt-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="text-xs font-medium text-blue-700 disabled:text-slate-300 hover:underline"
          >
            ← Previous
          </button>
          <span className="text-xs text-slate-400">Page {page} of {pages}</span>
          <button
            onClick={() => setPage((p) => Math.min(pages, p + 1))}
            disabled={page === pages}
            className="text-xs font-medium text-blue-700 disabled:text-slate-300 hover:underline"
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────

const TABS = ["Overview", "Deadlines", "Anomalies", "WhatsApp"];

export default function ClientDetailPage() {
  const { id } = useParams();
  const router  = useRouter();
  const [tab, setTab] = useState("Overview");

  const { data, isLoading, isError } = useQuery({
    queryKey: ["client-detail", id],
    queryFn: () => clientsApi.detail(id).then((r) => r.data.data),
    enabled: !!id,
  });

  if (isLoading) {
    return (
      <div className="p-5 space-y-4 animate-pulse">
        <div className="h-8 bg-slate-200 rounded w-40" />
        <div className="h-24 bg-slate-100 rounded-2xl" />
        <div className="grid grid-cols-2 gap-3">
          {[...Array(4)].map((_, i) => <div key={i} className="h-20 bg-slate-100 rounded-2xl" />)}
        </div>
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="p-5 text-center py-20">
        <p className="text-slate-500">Client not found.</p>
        <button onClick={() => router.back()} className="btn-outline mt-4">Go Back</button>
      </div>
    );
  }

  const { client, stats, compliance_color, compliance_score, days_since_last_entry } = data;
  const c = COMPLIANCE_COLORS[compliance_color] || COMPLIANCE_COLORS.green;

  return (
    <div className="p-5">
      {/* Back */}
      <button
        onClick={() => router.back()}
        className="flex items-center gap-2 text-sm text-slate-500 hover:text-slate-800 mb-4 transition-colors"
      >
        <ArrowLeft size={16} />
        Back to Clients
      </button>

      {/* Client header */}
      <div className="bg-white rounded-2xl border border-slate-200 p-5 mb-5">
        <div className="flex items-start gap-4">
          <div className="w-14 h-14 rounded-2xl bg-blue-100 flex items-center justify-center shrink-0">
            <span className="text-xl font-bold text-blue-700">{getInitials(client.name)}</span>
          </div>
          <div className="flex-1 min-w-0">
            <h1 className="text-lg font-bold text-slate-800 truncate">{client.name}</h1>
            <div className="flex items-center gap-2 mt-1 flex-wrap">
              {client.business_type && (
                <span className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full capitalize">
                  {client.business_type}
                </span>
              )}
              {client.state && (
                <span className="flex items-center gap-1 text-xs text-slate-400">
                  <MapPin size={10} /> {client.state}
                </span>
              )}
              <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${c.bg} ${c.text}`}>
                {c.label}
              </span>
            </div>
          </div>
        </div>

        {/* Meta info */}
        <div className="grid grid-cols-2 gap-3 mt-4 pt-4 border-t border-slate-100">
          {client.phone && (
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <Phone size={12} className="shrink-0 text-slate-400" />
              {client.phone}
            </div>
          )}
          {client.gstin && (
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <Hash size={12} className="shrink-0 text-slate-400" />
              GSTIN: {client.gstin}
            </div>
          )}
          {client.pan && (
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <FileText size={12} className="shrink-0 text-slate-400" />
              PAN: {client.pan}
            </div>
          )}
          {days_since_last_entry != null && (
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <Clock size={12} className="shrink-0 text-slate-400" />
              {days_since_last_entry === 0 ? "Entry today" : `${days_since_last_entry}d since last entry`}
            </div>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-200 mb-5">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2.5 text-sm font-medium transition-colors relative ${
              tab === t
                ? "text-blue-700"
                : "text-slate-500 hover:text-slate-700"
            }`}
          >
            {t}
            {tab === t && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-700 rounded-full" />
            )}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === "Overview"   && <OverviewTab detail={data} clientId={id} />}
      {tab === "Deadlines"  && <DeadlinesTab clientId={id} />}
      {tab === "Anomalies"  && <AnomaliesTab clientId={id} />}
      {tab === "WhatsApp"   && <WhatsAppTab clientId={id} />}
    </div>
  );
}
