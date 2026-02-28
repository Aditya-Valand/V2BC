/**
 * CA Public Profile Page — /ca/[orgId]
 *
 * Public, no auth required.
 * Displays firm name, city/state, ICAI license, client count, owner name.
 * Can be shared as a trust/marketing page for the CA firm.
 */
"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  Building2, MapPin, BadgeCheck, Users, Star, Phone,
  ArrowLeft, Share2, ExternalLink,
} from "lucide-react";
import apiClient from "@/lib/api/client";

// ── helpers ────────────────────────────────────────────────────────── //
const PLAN_LABEL = { free: "Standard", paid: "Professional" };
const PLAN_COLOR = {
  free: "bg-slate-100 text-slate-600",
  paid: "bg-amber-100 text-amber-700",
};

function StatCard({ icon: Icon, label, value, sub }) {
  return (
    <div className="bg-white rounded-2xl p-4 flex items-start gap-3 shadow-sm border border-slate-100">
      <div className="w-10 h-10 rounded-xl bg-blue-50 flex items-center justify-center shrink-0">
        <Icon size={18} className="text-blue-600" />
      </div>
      <div className="min-w-0">
        <p className="text-xs text-slate-500 mb-0.5">{label}</p>
        <p className="text-base font-bold text-slate-800 truncate">{value || "—"}</p>
        {sub && <p className="text-xs text-slate-400 mt-0.5">{sub}</p>}
      </div>
    </div>
  );
}

// ── page ───────────────────────────────────────────────────────────── //
export default function CaPublicProfilePage() {
  const { orgId }   = useParams();
  const [firm, setFirm]     = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]   = useState(null);

  useEffect(() => {
    if (!orgId) return;
    apiClient
      .get(`/orgs/${orgId}/public`)
      .then((res) => setFirm(res.data.data))
      .catch(() => setError("Firm not found or unavailable."))
      .finally(() => setLoading(false));
  }, [orgId]);

  const handleShare = async () => {
    const url  = window.location.href;
    const text = firm
      ? `${firm.name} — Trusted CA Firm on BharatCompliance\n${url}`
      : url;

    if (navigator.share) {
      await navigator.share({ title: firm?.name || "CA Profile", text, url }).catch(() => {});
    } else {
      await navigator.clipboard.writeText(url).catch(() => {});
      alert("Link copied to clipboard!");
    }
  };

  // ── loading state ── //
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="w-10 h-10 rounded-full border-4 border-blue-600 border-t-transparent animate-spin" />
      </div>
    );
  }

  // ── error state ── //
  if (error) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4 bg-slate-50 px-6">
        <Building2 size={48} className="text-slate-300" />
        <p className="text-slate-500 text-center">{error}</p>
        <Link href="/" className="text-blue-600 text-sm font-medium hover:underline">
          Go to BharatCompliance
        </Link>
      </div>
    );
  }

  const memberSince = firm.created_at
    ? new Date(firm.created_at).toLocaleDateString("en-IN", { year: "numeric", month: "long" })
    : null;

  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 via-slate-50 to-slate-50">

      {/* ── Topbar ── */}
      <div className="sticky top-0 z-10 bg-white/80 backdrop-blur border-b border-slate-200 px-4 py-3 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-1.5 text-slate-600 hover:text-slate-900">
          <ArrowLeft size={18} />
          <span className="text-sm font-medium">BharatCompliance</span>
        </Link>
        <button
          onClick={handleShare}
          className="flex items-center gap-1.5 text-blue-600 text-sm font-semibold hover:text-blue-800"
        >
          <Share2 size={16} />
          Share
        </button>
      </div>

      {/* ── Hero banner ── */}
      <div className="bg-gradient-to-br from-blue-700 to-blue-900 px-6 py-12 text-white text-center">
        <div className="w-20 h-20 rounded-2xl bg-white/20 backdrop-blur flex items-center justify-center mx-auto mb-4">
          <Building2 size={36} className="text-white" />
        </div>
        <h1 className="text-2xl font-bold mb-1">{firm.name}</h1>
        {firm.owner_name && (
          <p className="text-blue-200 text-sm mb-3">CA {firm.owner_name}</p>
        )}
        <div className="flex items-center justify-center gap-1.5 text-blue-100 text-sm">
          <MapPin size={14} />
          <span>
            {[firm.city, firm.state].filter(Boolean).join(", ") || "India"}
          </span>
        </div>

        {/* Verified badge */}
        <div className="inline-flex items-center gap-1.5 mt-4 bg-white/15 rounded-full px-3 py-1.5 text-xs font-semibold">
          <BadgeCheck size={14} className="text-green-300" />
          Verified on BharatCompliance
        </div>
      </div>

      {/* ── Stats grid ── */}
      <div className="px-4 -mt-4">
        <div className="grid grid-cols-2 gap-3">
          <StatCard
            icon={Users}
            label="Active Clients"
            value={firm.client_count ?? "—"}
            sub="businesses served"
          />
          <StatCard
            icon={Star}
            label="Plan"
            value={PLAN_LABEL[firm.plan] || firm.plan}
            sub={firm.plan === "paid" ? "Premium features" : ""}
          />
          {firm.license_number && (
            <StatCard
              icon={BadgeCheck}
              label="ICAI Membership"
              value={firm.license_number}
              sub="Registered CA"
            />
          )}
          {memberSince && (
            <StatCard
              icon={Building2}
              label="Member Since"
              value={memberSince}
              sub="on BharatCompliance"
            />
          )}
        </div>
      </div>

      {/* ── About ── */}
      <div className="mx-4 mt-4 bg-white rounded-2xl p-5 shadow-sm border border-slate-100">
        <h2 className="text-sm font-bold text-slate-700 mb-3">About this Firm</h2>
        <p className="text-sm text-slate-600 leading-relaxed">
          {firm.name} is a registered CA firm{firm.city ? ` based in ${firm.city}` : ""}{firm.state ? `, ${firm.state}` : ""}, serving micro-businesses and
          freelancers with GST compliance, bookkeeping, and financial advisory
          through BharatCompliance.
        </p>
      </div>

      {/* ── Services ── */}
      <div className="mx-4 mt-4 bg-white rounded-2xl p-5 shadow-sm border border-slate-100">
        <h2 className="text-sm font-bold text-slate-700 mb-3">Services Offered</h2>
        <div className="grid grid-cols-2 gap-2">
          {["GST Filing", "Bookkeeping", "ITR Filing", "Business Registration",
            "TDS Compliance", "Financial Advisory"].map((s) => (
            <div key={s} className="flex items-center gap-2 text-sm text-slate-700">
              <BadgeCheck size={13} className="text-green-500 shrink-0" />
              {s}
            </div>
          ))}
        </div>
      </div>

      {/* ── CTA ── */}
      <div className="mx-4 mt-4 mb-8 bg-gradient-to-r from-blue-600 to-blue-800 rounded-2xl p-5 text-white">
        <h2 className="font-bold mb-1">Want to get started?</h2>
        <p className="text-blue-100 text-sm mb-4">
          Ask your CA for an invite link to join BharatCompliance and track your business compliance effortlessly.
        </p>
        <a
          href="https://bharatcomplianceb.onrender.com"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 bg-white text-blue-700 font-semibold text-sm px-4 py-2 rounded-xl hover:bg-blue-50 transition-colors"
        >
          Learn More
          <ExternalLink size={14} />
        </a>
      </div>

      {/* ── Footer ── */}
      <p className="text-center text-xs text-slate-400 pb-6">
        Powered by BharatCompliance · India&apos;s WhatsApp-first compliance platform
      </p>
    </div>
  );
}
