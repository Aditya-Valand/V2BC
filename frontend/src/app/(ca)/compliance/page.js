"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import {
  ShieldCheck, AlertTriangle, TrendingUp, Eye, CheckCheck,
  ChevronRight, RefreshCw, Flame, Activity, FileWarning,
  BellRing, Check,
} from "lucide-react";
import { toast } from "sonner";
import { format } from "date-fns";
import { complianceApi } from "@/lib/api/compliance";
import { getApiError } from "@/lib/api/client";
import { ALERT_SEVERITY } from "@/constants";
import { formatINR, formatDate, getInitials } from "@/lib/utils";
import useAuthStore from "@/store/authStore";

// ── Helpers ───────────────────────────────────────────────────────────

const GST_RISK = {
  low:      { label: "Low",      cls: "bg-green-100 text-green-700"  },
  medium:   { label: "Medium",   cls: "bg-yellow-100 text-yellow-700" },
  high:     { label: "High",     cls: "bg-orange-100 text-orange-700" },
  critical: { label: "Critical", cls: "bg-red-100 text-red-700"      },
};

function ScoreBar({ value, max = 100 }) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100));
  const color = value >= 70 ? "bg-green-500" : value >= 40 ? "bg-yellow-400" : "bg-red-500";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-bold text-slate-700 w-7 text-right">{Math.round(value)}</span>
    </div>
  );
}

// ── Skeleton ──────────────────────────────────────────────────────────

function Skeleton({ className = "" }) {
  return <div className={`bg-slate-200 animate-pulse rounded-xl ${className}`} />;
}

// ── Risk Overview Tab ─────────────────────────────────────────────────

function RiskTab({ data }) {
  if (!data) return null;
  const {
    total_businesses,
    risky_businesses,
    approaching_gst_threshold,
    weak_evidence_businesses,
    open_alerts_summary,
  } = data;

  const summaryCards = [
    {
      label: "Total Businesses",
      value: total_businesses ?? "—",
      icon: Activity,
      color: "bg-blue-50 text-blue-700",
    },
    {
      label: "Risky",
      value: risky_businesses?.count ?? 0,
      icon: Flame,
      color: risky_businesses?.count > 0 ? "bg-red-50 text-red-700" : "bg-slate-100 text-slate-600",
    },
    {
      label: "Near GST Limit",
      value: approaching_gst_threshold?.count ?? 0,
      icon: TrendingUp,
      color: approaching_gst_threshold?.count > 0 ? "bg-orange-50 text-orange-700" : "bg-slate-100 text-slate-600",
    },
    {
      label: "Weak Evidence",
      value: weak_evidence_businesses?.count ?? 0,
      icon: FileWarning,
      color: weak_evidence_businesses?.count > 0 ? "bg-yellow-50 text-yellow-700" : "bg-slate-100 text-slate-600",
    },
  ];

  return (
    <div className="space-y-6">
      {/* Summary grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {summaryCards.map(({ label, value, icon: Icon, color }) => (
          <div key={label} className={`rounded-2xl p-4 ${color}`}>
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs font-medium opacity-70">{label}</p>
              <Icon size={16} className="opacity-50" />
            </div>
            <p className="text-3xl font-bold">{value}</p>
          </div>
        ))}
      </div>

      {/* Open alerts summary */}
      {open_alerts_summary && (
        <div className="bg-white rounded-2xl border border-slate-200 p-4">
          <p className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2">
            <BellRing size={15} className="text-orange-500" />
            Open Alerts
          </p>
          <div className="flex flex-wrap gap-2">
            {["critical", "high", "medium", "low"].map((sev) => {
              const count = open_alerts_summary[sev];
              if (!count) return null;
              const s = ALERT_SEVERITY[sev];
              return (
                <span key={sev} className={`text-xs font-semibold px-3 py-1 rounded-full border ${s.bg} ${s.text} ${s.border}`}>
                  {count} {s.label}
                </span>
              );
            })}
            {open_alerts_summary.total === 0 && (
              <span className="text-sm text-slate-400">No open alerts — all clear.</span>
            )}
          </div>
        </div>
      )}

      {/* Risky businesses */}
      {risky_businesses?.list?.length > 0 && (
        <Section
          title="Risky Businesses"
          icon={Flame}
          iconColor="text-red-500"
          items={risky_businesses.list}
          renderItem={(b) => (
            <BusinessRiskRow
              key={b.business_id}
              id={b.business_id}
              name={b.business_name}
              score={b.discipline_score}
              evidenceHealth={b.evidence_health}
              turnover={b.estimated_turnover}
              gstRisk={b.gst_risk_level}
            />
          )}
        />
      )}

      {/* Approaching GST */}
      {approaching_gst_threshold?.list?.length > 0 && (
        <Section
          title="Approaching GST Threshold"
          icon={TrendingUp}
          iconColor="text-orange-500"
          subtitle="These clients may need GST registration"
          items={approaching_gst_threshold.list}
          renderItem={(b) => (
            <BusinessRiskRow
              key={b.business_id}
              id={b.business_id}
              name={b.business_name}
              turnover={b.estimated_turnover}
              gstRisk={b.gst_risk_level}
              showTurnover
            />
          )}
        />
      )}

      {/* Weak evidence */}
      {weak_evidence_businesses?.list?.length > 0 && (
        <Section
          title="Weak Evidence"
          icon={FileWarning}
          iconColor="text-yellow-500"
          subtitle="Low-quality or missing receipts/bills"
          items={weak_evidence_businesses.list}
          renderItem={(b) => (
            <BusinessRiskRow
              key={b.business_id}
              id={b.business_id}
              name={b.business_name}
              evidenceHealth={b.evidence_health}
            />
          )}
        />
      )}

      {risky_businesses?.count === 0 &&
       approaching_gst_threshold?.count === 0 &&
       weak_evidence_businesses?.count === 0 && (
        <div className="bg-green-50 border border-green-200 rounded-2xl p-8 text-center">
          <ShieldCheck size={40} className="text-green-500 mx-auto mb-3" />
          <p className="text-base font-bold text-green-800">All Clear!</p>
          <p className="text-sm text-green-600 mt-1">No compliance risks detected across all clients.</p>
        </div>
      )}
    </div>
  );
}

function Section({ title, icon: Icon, iconColor, subtitle, items, renderItem }) {
  return (
    <div>
      <div className="flex items-center gap-2 mb-3">
        <Icon size={16} className={iconColor} />
        <h3 className="text-sm font-bold text-slate-700">{title}</h3>
        <span className="text-xs text-slate-400 font-normal ml-1">{items.length}</span>
      </div>
      {subtitle && <p className="text-xs text-slate-400 mb-3 -mt-2">{subtitle}</p>}
      <div className="bg-white rounded-2xl border border-slate-200 divide-y divide-slate-100 overflow-hidden">
        {items.map(renderItem)}
      </div>
    </div>
  );
}

function BusinessRiskRow({ id, name, score, evidenceHealth, turnover, gstRisk, showTurnover }) {
  const risk = GST_RISK[gstRisk] || GST_RISK.low;
  return (
    <Link
      href={`/clients/${id}`}
      className="flex items-center gap-3 px-4 py-3 hover:bg-slate-50 transition-colors group"
    >
      <div className="w-9 h-9 rounded-full bg-slate-100 flex items-center justify-center shrink-0">
        <span className="text-xs font-bold text-slate-600">{getInitials(name)}</span>
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-slate-800 truncate">{name}</p>
        {score != null && <ScoreBar value={score} />}
        {evidenceHealth != null && score == null && (
          <div className="flex items-center gap-1 mt-0.5">
            <span className="text-xs text-slate-400">Evidence:</span>
            <ScoreBar value={evidenceHealth} />
          </div>
        )}
        {showTurnover && turnover != null && (
          <p className="text-xs text-slate-400 mt-0.5">Turnover: {formatINR(turnover)}</p>
        )}
      </div>
      <div className="flex items-center gap-2 shrink-0">
        {gstRisk && (
          <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${risk.cls}`}>
            GST: {risk.label}
          </span>
        )}
        <ChevronRight size={14} className="text-slate-300 group-hover:text-slate-500" />
      </div>
    </Link>
  );
}

// ── Rankings Tab ──────────────────────────────────────────────────────

function RankingsTab({ orgId }) {
  const { data, isLoading } = useQuery({
    queryKey: ["discipline-ranking", orgId],
    queryFn: () => complianceApi.disciplineRanking(orgId).then((r) => r.data),
    enabled: !!orgId,
  });

  if (isLoading) return (
    <div className="space-y-3">
      {[...Array(8)].map((_, i) => <Skeleton key={i} className="h-14" />)}
    </div>
  );

  const top    = data?.top_compliant    || [];
  const bottom = data?.bottom_compliant || [];

  return (
    <div className="space-y-6">
      {/* Top compliant */}
      <div>
        <div className="flex items-center gap-2 mb-3">
          <div className="w-5 h-5 bg-green-100 rounded-full flex items-center justify-center">
            <span className="text-[10px]">🏆</span>
          </div>
          <h3 className="text-sm font-bold text-slate-700">Most Compliant</h3>
        </div>
        <div className="bg-white rounded-2xl border border-slate-200 divide-y divide-slate-100 overflow-hidden">
          {top.length === 0 ? (
            <p className="px-4 py-6 text-sm text-slate-400 text-center">No data yet.</p>
          ) : top.map((b, i) => (
            <RankRow key={b.business_id} rank={i + 1} business={b} variant="top" />
          ))}
        </div>
      </div>

      {/* Bottom compliant */}
      <div>
        <div className="flex items-center gap-2 mb-3">
          <div className="w-5 h-5 bg-red-100 rounded-full flex items-center justify-center">
            <span className="text-[10px]">⚠️</span>
          </div>
          <h3 className="text-sm font-bold text-slate-700">Needs Most Attention</h3>
        </div>
        <div className="bg-white rounded-2xl border border-slate-200 divide-y divide-slate-100 overflow-hidden">
          {bottom.length === 0 ? (
            <p className="px-4 py-6 text-sm text-slate-400 text-center">No data yet.</p>
          ) : bottom.map((b, i) => (
            <RankRow key={b.business_id} rank={i + 1} business={b} variant="bottom" />
          ))}
        </div>
      </div>
    </div>
  );
}

function RankRow({ rank, business, variant }) {
  const score = business.discipline_score ?? 0;
  return (
    <Link
      href={`/clients/${business.business_id}`}
      className="flex items-center gap-3 px-4 py-3 hover:bg-slate-50 transition-colors group"
    >
      <span className={`text-sm font-bold w-6 text-center shrink-0 ${
        variant === "top" ? "text-green-600" : "text-red-500"
      }`}>
        #{rank}
      </span>
      <div className="w-9 h-9 rounded-full bg-slate-100 flex items-center justify-center shrink-0">
        <span className="text-xs font-bold text-slate-600">{getInitials(business.business_name)}</span>
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-slate-800 truncate">{business.business_name}</p>
        <ScoreBar value={score} />
      </div>
      <ChevronRight size={14} className="text-slate-300 group-hover:text-slate-500 shrink-0" />
    </Link>
  );
}

// ── Alerts Tab ────────────────────────────────────────────────────────

function AlertsTab({ orgId }) {
  const qc = useQueryClient();
  const [sevFilter, setSevFilter] = useState("all");

  const { data, isLoading } = useQuery({
    queryKey: ["open-alerts", orgId, sevFilter],
    queryFn: () =>
      complianceApi
        .openAlerts(orgId, sevFilter !== "all" ? { severity: sevFilter } : {})
        .then((r) => r.data),
    enabled: !!orgId,
  });

  const acknowledgeMutation = useMutation({
    mutationFn: (id) => complianceApi.acknowledgeAlert(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["open-alerts", orgId] });
      qc.invalidateQueries({ queryKey: ["risk-summary", orgId] });
      toast.success("Alert acknowledged.");
    },
    onError: (err) => toast.error(getApiError(err)),
  });

  const resolveMutation = useMutation({
    mutationFn: (id) => complianceApi.resolveAlert(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["open-alerts", orgId] });
      qc.invalidateQueries({ queryKey: ["risk-summary", orgId] });
      toast.success("Alert resolved.");
    },
    onError: (err) => toast.error(getApiError(err)),
  });

  const alerts = data?.alerts || (Array.isArray(data) ? data : []);

  return (
    <div className="space-y-4">
      {/* Severity filter */}
      <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide">
        {["all", "critical", "high", "medium", "low"].map((s) => (
          <button
            key={s}
            onClick={() => setSevFilter(s)}
            className={`shrink-0 text-xs font-semibold px-3 py-1.5 rounded-full border transition-colors ${
              sevFilter === s
                ? "bg-blue-700 text-white border-blue-700"
                : "bg-white text-slate-600 border-slate-200 hover:border-blue-300"
            }`}
          >
            {s === "all" ? "All" : s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      {/* Alerts list */}
      {isLoading ? (
        <div className="space-y-3">
          {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-20" />)}
        </div>
      ) : alerts.length === 0 ? (
        <div className="bg-green-50 border border-green-200 rounded-2xl p-10 text-center">
          <ShieldCheck size={36} className="text-green-500 mx-auto mb-2" />
          <p className="text-sm font-semibold text-green-800">No open alerts</p>
          <p className="text-xs text-green-600 mt-1">All {sevFilter !== "all" ? sevFilter : ""} alerts resolved.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {alerts.map((alert) => {
            const s = ALERT_SEVERITY[alert.severity] || ALERT_SEVERITY.low;
            return (
              <div
                key={alert.id}
                className={`rounded-2xl border p-4 ${s.bg} ${s.border}`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <span className={`text-[11px] font-bold px-2 py-0.5 rounded-full ${s.bg} ${s.text} border ${s.border}`}>
                        {s.label}
                      </span>
                      {alert.business_name && (
                        <Link
                          href={`/clients/${alert.business_id}`}
                          className={`text-xs font-semibold underline ${s.text}`}
                        >
                          {alert.business_name}
                        </Link>
                      )}
                    </div>
                    <p className={`text-sm font-semibold ${s.text}`}>{alert.title}</p>
                    <p className="text-xs text-slate-500 mt-1">
                      {formatDate(alert.created_at, "d MMM yyyy · HH:mm")}
                    </p>
                  </div>
                </div>
                {/* Actions */}
                <div className="flex gap-2 mt-3">
                  {!alert.acknowledged_at && (
                    <button
                      onClick={() => acknowledgeMutation.mutate(alert.id)}
                      disabled={acknowledgeMutation.isPending}
                      className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-white/70 border border-current text-slate-700 hover:bg-white transition-colors flex items-center gap-1.5"
                    >
                      <Eye size={12} /> Acknowledge
                    </button>
                  )}
                  {!alert.resolved_at && (
                    <button
                      onClick={() => resolveMutation.mutate(alert.id)}
                      disabled={resolveMutation.isPending}
                      className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-white/70 border border-current text-slate-700 hover:bg-white transition-colors flex items-center gap-1.5"
                    >
                      <CheckCheck size={12} /> Resolve
                    </button>
                  )}
                  {alert.acknowledged_at && alert.resolved_at && (
                    <span className="text-xs text-slate-400 italic flex items-center gap-1">
                      <Check size={11} /> Resolved
                    </span>
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

// ── Main Page ─────────────────────────────────────────────────────────

const TABS = [
  { key: "risk",     label: "Risk Overview", icon: Flame      },
  { key: "rankings", label: "Rankings",      icon: Activity    },
  { key: "alerts",   label: "Alerts",        icon: BellRing    },
];

export default function CompliancePage() {
  const orgId = useAuthStore((s) => s.getOrgId());
  const [tab, setTab] = useState("risk");

  const { data, isLoading, refetch, isFetching } = useQuery({
    queryKey: ["risk-summary", orgId],
    queryFn: () => complianceApi.riskSummary(orgId).then((r) => r.data),
    enabled: !!orgId,
  });

  const alertCount = data?.open_alerts_summary?.total ?? 0;

  return (
    <div className="max-w-4xl mx-auto">
      {/* Page header */}
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-xl font-bold text-slate-800">Compliance</h1>
          <p className="text-sm text-slate-400 mt-0.5">Risk monitoring across all clients</p>
        </div>
        <button
          onClick={() => refetch()}
          disabled={isFetching}
          className="flex items-center gap-2 text-sm text-slate-500 hover:text-blue-700 transition-colors"
        >
          <RefreshCw size={15} className={isFetching ? "animate-spin" : ""} />
          <span className="hidden sm:inline">Refresh</span>
        </button>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-200 mb-6">
        {TABS.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium transition-colors relative ${
              tab === key ? "text-blue-700" : "text-slate-500 hover:text-slate-700"
            }`}
          >
            <Icon size={15} />
            {label}
            {key === "alerts" && alertCount > 0 && (
              <span className="ml-1 min-w-[18px] h-[18px] bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center px-1">
                {alertCount > 99 ? "99+" : alertCount}
              </span>
            )}
            {tab === key && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-700 rounded-full" />
            )}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === "risk" && (
        isLoading
          ? <div className="space-y-3">{[...Array(4)].map((_, i) => <Skeleton key={i} className="h-20" />)}</div>
          : <RiskTab data={data} />
      )}
      {tab === "rankings" && <RankingsTab orgId={orgId} />}
      {tab === "alerts"   && <AlertsTab   orgId={orgId} />}
    </div>
  );
}
