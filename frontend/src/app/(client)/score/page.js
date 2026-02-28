"use client";

import { useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Share2, MessageCircle, ShieldCheck, TrendingUp, RefreshCw,
  ChevronRight, AlertTriangle,
} from "lucide-react";
import { toast } from "sonner";
import { format, parseISO } from "date-fns";
import { transactionsApi } from "@/lib/api/transactions";
import { formatINR } from "@/lib/utils";
import useAuthStore from "@/store/authStore";
import { useLang } from "@/lib/i18n";

// ── Score ring (pure CSS conic-gradient) ──────────────────────────────

function ScoreRing({ score, grade, gradeLabel, color }) {
  const pct = Math.max(0, Math.min(100, score));
  // conic-gradient: filled arc = score%, rest = track
  const filled = `hsl(${color})`;

  return (
    <div className="relative flex items-center justify-center" style={{ width: 160, height: 160 }}>
      {/* Track + fill via two nested divs */}
      <div
        className="absolute inset-0 rounded-full"
        style={{
          background: `conic-gradient(${filled} ${pct}%, #e2e8f0 ${pct}%)`,
        }}
      />
      {/* White inner circle */}
      <div className="absolute rounded-full bg-white" style={{ inset: 14 }} />
      {/* Score text */}
      <div className="relative flex flex-col items-center">
        <span className="text-5xl font-black text-slate-800 leading-none">{score}</span>
        <span className="text-xs font-semibold text-slate-400 mt-1">out of 100</span>
        <span
          className="mt-1.5 text-xs font-bold px-2.5 py-0.5 rounded-full text-white"
          style={{ background: `hsl(${color})` }}
        >
          Grade {grade}
        </span>
      </div>
    </div>
  );
}

// ── Metric row ────────────────────────────────────────────────────────

function MetricRow({ icon: Icon, label, value, sub, color = "text-slate-500" }) {
  return (
    <div className="flex items-center gap-3 py-3 border-b border-slate-100 last:border-0">
      <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${color} bg-current/10`}>
        <Icon size={15} className={color} style={{ color: "inherit" }} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-xs font-semibold text-slate-600">{label}</p>
        {sub && <p className="text-[11px] text-slate-400 mt-0.5">{sub}</p>}
      </div>
      <span className="text-sm font-bold text-slate-700 shrink-0">{value}</span>
    </div>
  );
}

// ── Share card (the design that gets shared) ──────────────────────────

function ShareCard({ data, cardRef }) {
  const { score, grade, gradeLabel, business_name, ca_name, gst_risk_level } = data;

  const scoreColor =
    score >= 80 ? "142 72% 45%"   // green
    : score >= 60 ? "38 92% 50%"  // amber
    : score >= 40 ? "25 95% 53%"  // orange
    : "0 84% 60%";                // red

  const gstBadge = {
    low:    { label: "Low Risk",    cls: "bg-green-100 text-green-700"  },
    medium: { label: "Medium Risk", cls: "bg-yellow-100 text-yellow-700" },
    high:   { label: "High Risk",   cls: "bg-red-100 text-red-700"      },
  }[gst_risk_level] || { label: "Low Risk", cls: "bg-green-100 text-green-700" };

  return (
    <div
      ref={cardRef}
      className="bg-gradient-to-br from-blue-700 via-blue-800 to-indigo-900 rounded-3xl p-6 text-white shadow-2xl"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-white/20 rounded-xl flex items-center justify-center">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
              <path d="M12 2L2 7l10 5 10-5-10-5z" fill="white" />
              <path d="M2 17l10 5 10-5" stroke="white" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </div>
          <span className="text-sm font-bold">BharatCompliance</span>
        </div>
        <ShieldCheck size={18} className="opacity-60" />
      </div>

      {/* Business name */}
      <p className="text-lg font-black leading-tight mb-1">{business_name}</p>
      {ca_name && (
        <p className="text-xs text-white/60 mb-5">Managed by {ca_name} (CA)</p>
      )}

      {/* Score */}
      <div className="flex items-center gap-5 mb-5">
        {/* Mini ring */}
        <div className="relative flex items-center justify-center shrink-0" style={{ width: 100, height: 100 }}>
          <div
            className="absolute inset-0 rounded-full"
            style={{
              background: `conic-gradient(white ${score}%, rgba(255,255,255,0.15) ${score}%)`,
            }}
          />
          <div className="absolute rounded-full bg-blue-800" style={{ inset: 10 }} />
          <div className="relative flex flex-col items-center">
            <span className="text-3xl font-black leading-none">{score}</span>
            <span className="text-[10px] text-white/60">/100</span>
          </div>
        </div>

        <div>
          <p className="text-4xl font-black">Grade</p>
          <p className="text-6xl font-black leading-none" style={{
            textShadow: "0 0 30px rgba(255,255,255,0.3)"
          }}>{grade}</p>
          <p className="text-xs text-white/70 mt-1">{gradeLabel}</p>
        </div>
      </div>

      {/* GST risk badge */}
      <div className="flex items-center gap-2 mb-4">
        <span className={`text-xs font-bold px-3 py-1 rounded-full ${gstBadge.cls}`}>
          GST: {gstBadge.label}
        </span>
        <span className="text-xs text-white/50">•</span>
        <span className="text-xs text-white/60">{format(new Date(), "MMMM yyyy")}</span>
      </div>

      {/* Footer */}
      <div className="border-t border-white/20 pt-3 mt-2">
        <p className="text-[11px] text-white/50 text-center">
          Verified by BharatCompliance — India's micro-business compliance platform
        </p>
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────

export default function ScorePage() {
  const { user } = useAuthStore();
  const { t } = useLang();
  const cardRef = useRef(null);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["my-compliance-score"],
    queryFn:  () => transactionsApi.complianceScore().then((r) => r.data.data),
    staleTime: 1000 * 60 * 5,
  });

  const gradeMap = {
    A: { label: t("score.grade_a"), scoreColor: "142 72% 45%", textColor: "text-green-600",  bg: "bg-green-50",  border: "border-green-200" },
    B: { label: t("score.grade_b"), scoreColor: "38 92% 50%",  textColor: "text-amber-600",  bg: "bg-amber-50",  border: "border-amber-200" },
    C: { label: t("score.grade_c"), scoreColor: "25 95% 53%",  textColor: "text-orange-600", bg: "bg-orange-50", border: "border-orange-200" },
    D: { label: t("score.grade_d"), scoreColor: "0 84% 60%",   textColor: "text-red-600",    bg: "bg-red-50",    border: "border-red-200"   },
  };

  const handleShare = async () => {
    if (!data) return;
    const msg = t("score.share_msg", { score: data.score, grade: data.grade });
    const shareData = {
      title: "My BharatCompliance Score",
      text:  msg,
    };

    if (navigator.share && navigator.canShare?.(shareData)) {
      try {
        await navigator.share(shareData);
      } catch (e) {
        if (e.name !== "AbortError") openWhatsApp(msg);
      }
    } else {
      openWhatsApp(msg);
    }
  };

  const openWhatsApp = (msg) => {
    const encoded = encodeURIComponent(msg);
    window.open(`https://wa.me/?text=${encoded}`, "_blank", "noopener");
  };

  const handleWhatsApp = () => {
    if (!data) return;
    const msg = t("score.share_msg", { score: data.score, grade: data.grade });
    openWhatsApp(msg);
  };

  if (isLoading) {
    return (
      <div className="p-4 space-y-4">
        <div className="h-6 bg-slate-200 animate-pulse rounded w-32" />
        <div className="h-64 bg-slate-200 animate-pulse rounded-3xl" />
        <div className="h-40 bg-slate-200 animate-pulse rounded-2xl" />
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="p-4 flex flex-col items-center justify-center min-h-[50vh] gap-4">
        <AlertTriangle size={40} className="text-orange-400" />
        <p className="text-sm text-slate-500 text-center">{t("common.error")}</p>
        <button
          onClick={() => refetch()}
          className="flex items-center gap-2 text-sm font-semibold text-blue-700"
        >
          <RefreshCw size={14} /> {t("common.retry")}
        </button>
      </div>
    );
  }

  const grade    = data.grade || "B";
  const gm       = gradeMap[grade] || gradeMap.B;
  const gradeLabel = gm.label;
  const scoreColor = gm.scoreColor;

  const evidencePct = data.evidence_health ?? 50;
  const gstRiskMap  = { low: t("score.gst_low"), medium: t("score.gst_medium"), high: t("score.gst_high") };
  const gstLabel    = gstRiskMap[data.gst_risk_level] || t("score.gst_low");

  return (
    <div className="p-4 pb-8 space-y-4">

      {/* Page title */}
      <div>
        <p className="text-xs font-medium text-slate-400 uppercase tracking-wide">
          {user?.name?.split(" ")[0]}
        </p>
        <h1 className="text-xl font-bold text-slate-800">{t("score.title")}</h1>
      </div>

      {/* ── Share card ── */}
      <ShareCard
        cardRef={cardRef}
        data={{ ...data, gradeLabel }}
      />

      {/* ── Score ring (detailed view) ── */}
      <div className={`bg-white rounded-2xl border ${gm.border} p-6 flex flex-col items-center gap-4`}>
        <ScoreRing score={data.score} grade={grade} gradeLabel={gradeLabel} color={scoreColor} />
        <div className="text-center">
          <p className={`text-base font-bold ${gm.textColor}`}>{gradeLabel}</p>
          {data.last_updated && (
            <p className="text-xs text-slate-400 mt-0.5">
              {t("score.last_updated")} {format(parseISO(data.last_updated), "d MMM yyyy")}
            </p>
          )}
        </div>
      </div>

      {/* ── Metrics breakdown ── */}
      <div className="bg-white rounded-2xl border border-slate-200 px-4">
        <MetricRow
          icon={ShieldCheck}
          label={t("score.evidence")}
          value={`${evidencePct}/100`}
          sub={`${evidencePct >= 70 ? "Good" : evidencePct >= 40 ? "Needs improvement" : "Poor"} backing`}
          color="text-blue-600"
        />
        <MetricRow
          icon={TrendingUp}
          label={t("score.gst_risk")}
          value={gstLabel}
          sub={
            data.gst_risk_level === "high"
              ? "Annual turnover > ₹40L — GST registration required"
              : data.gst_risk_level === "medium"
              ? "Approaching GST threshold (₹20–40L)"
              : "Annual turnover below GST threshold"
          }
          color={data.gst_risk_level === "high" ? "text-red-500" : data.gst_risk_level === "medium" ? "text-amber-500" : "text-green-500"}
        />
      </div>

      {/* ── What affects your score ── */}
      <div className="bg-slate-50 rounded-2xl border border-slate-200 p-4">
        <p className="text-xs font-bold text-slate-600 mb-3 uppercase tracking-wide">How to improve</p>
        <div className="space-y-2">
          {[
            { check: data.score >= 80,   ok: "Transactions recorded regularly",              warn: "Record transactions more regularly" },
            { check: evidencePct >= 70,  ok: "Strong receipt backing",                       warn: "Upload more receipt photos" },
            { check: data.gst_risk_level !== "high", ok: "GST threshold not exceeded",       warn: "GST registration may be required" },
          ].map(({ check, ok, warn }, i) => (
            <div key={i} className="flex items-start gap-2">
              <span className={`mt-0.5 shrink-0 w-4 h-4 rounded-full flex items-center justify-center text-[10px] font-bold ${check ? "bg-green-100 text-green-700" : "bg-orange-100 text-orange-700"}`}>
                {check ? "✓" : "!"}
              </span>
              <p className="text-xs text-slate-600">{check ? ok : warn}</p>
            </div>
          ))}
        </div>
      </div>

      {/* ── Share buttons ── */}
      <div className="space-y-3">
        <button
          onClick={handleWhatsApp}
          className="w-full flex items-center justify-center gap-2.5 bg-green-600 hover:bg-green-700 active:scale-[0.98] text-white font-bold text-sm py-3.5 rounded-2xl transition-all shadow-md"
        >
          <MessageCircle size={18} />
          {t("score.share_wa")}
        </button>
        <button
          onClick={handleShare}
          className="w-full flex items-center justify-center gap-2.5 bg-blue-700 hover:bg-blue-800 active:scale-[0.98] text-white font-bold text-sm py-3.5 rounded-2xl transition-all"
        >
          <Share2 size={18} />
          {t("score.share")}
        </button>
      </div>

      {/* CA info */}
      {data.ca_name && (
        <div className="flex items-center justify-between bg-white rounded-2xl border border-slate-200 px-4 py-3">
          <p className="text-xs text-slate-500">{t("score.managed_by")}</p>
          <div className="flex items-center gap-1.5">
            <span className="text-sm font-semibold text-slate-700">{data.ca_name}</span>
            <span className="text-[10px] bg-blue-100 text-blue-700 font-bold px-1.5 py-0.5 rounded">CA</span>
          </div>
        </div>
      )}

    </div>
  );
}
