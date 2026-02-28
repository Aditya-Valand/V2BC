"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import {
  User, Phone, Building2, Shield, Eye, EyeOff,
  ArrowLeft, Loader2, Lock, CheckCircle2,
  Star, FileText, Globe, LogOut, ChevronRight, Receipt, Upload,
} from "lucide-react";
import { authApi } from "@/lib/api/auth";
import { getApiError } from "@/lib/api/client";
import { getInitials } from "@/lib/utils";
import useAuthStore from "@/store/authStore";
import { useLang } from "@/lib/i18n";

// ── Sub-components ─────────────────────────────────────────────────────

function InfoRow({ icon: Icon, label, value }) {
  return (
    <div className="flex items-center gap-3 px-4 py-3.5">
      <div className="w-8 h-8 bg-slate-100 rounded-xl flex items-center justify-center shrink-0">
        <Icon size={14} className="text-slate-500" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-xs text-slate-400">{label}</p>
        <p className="text-sm font-semibold text-slate-700 truncate mt-0.5">{value || "—"}</p>
      </div>
    </div>
  );
}

function PINField({ label, value, show, onToggle, onChange, error, placeholder }) {
  return (
    <div>
      <label className="block text-sm font-medium text-slate-700 mb-1.5">{label}</label>
      <div className="relative">
        <Lock size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
        <input
          type={show ? "text" : "password"}
          inputMode="numeric"
          maxLength={6}
          value={value}
          onChange={(e) => onChange(e.target.value.replace(/\D/g, "").slice(0, 6))}
          placeholder={placeholder}
          className={`input-base pl-10 pr-10 ${error ? "!border-red-400 !ring-red-200" : ""}`}
        />
        <button
          type="button"
          onClick={onToggle}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
        >
          {show ? <EyeOff size={16} /> : <Eye size={16} />}
        </button>
      </div>
      {error && <p className="text-red-500 text-xs mt-1">{error}</p>}
    </div>
  );
}

// ── Language toggle ────────────────────────────────────────────────────

function LanguageToggle({ lang, setLang, t }) {
  return (
    <div className="flex items-center gap-3 px-4 py-4">
      <div className="w-9 h-9 bg-slate-100 rounded-xl flex items-center justify-center shrink-0">
        <Globe size={16} className="text-slate-600" />
      </div>
      <div className="flex-1">
        <p className="text-sm font-semibold text-slate-700">{t("profile.language")}</p>
        <p className="text-xs text-slate-400 mt-0.5">App display language</p>
      </div>
      {/* Toggle pill */}
      <div className="flex bg-slate-100 rounded-xl p-0.5 gap-0.5 shrink-0">
        {["en", "hi"].map((l) => (
          <button
            key={l}
            onClick={() => setLang(l)}
            className={`px-3 py-1.5 rounded-[10px] text-xs font-bold transition-all ${
              lang === l
                ? "bg-blue-700 text-white shadow-sm"
                : "text-slate-500 hover:text-slate-700"
            }`}
          >
            {l === "en" ? t("profile.english") : t("profile.hindi")}
          </button>
        ))}
      </div>
    </div>
  );
}

// ── Quick link row ─────────────────────────────────────────────────────

function LinkRow({ icon: Icon, label, sub, href, iconBg = "bg-slate-100", iconColor = "text-slate-600" }) {
  return (
    <Link
      href={href}
      className="flex items-center gap-3 px-4 py-4 hover:bg-slate-50 active:bg-slate-100 transition-colors"
    >
      <div className={`w-9 h-9 ${iconBg} rounded-xl flex items-center justify-center shrink-0`}>
        <Icon size={16} className={iconColor} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-slate-700">{label}</p>
        {sub && <p className="text-xs text-slate-400 mt-0.5">{sub}</p>}
      </div>
      <ChevronRight size={14} className="text-slate-300 shrink-0" />
    </Link>
  );
}

// ── Main page ──────────────────────────────────────────────────────────

export default function ClientProfilePage() {
  const router = useRouter();
  const { user, org, logout } = useAuthStore();
  const { t, lang, setLang } = useLang();

  const [showPinForm, setShowPinForm] = useState(false);
  const [pinDone,     setPinDone]     = useState(false);
  const [loading,     setLoading]     = useState(false);
  const [errors,      setErrors]      = useState({});

  const [form, setForm] = useState({ current: "", next: "", confirm: "" });
  const [show, setShow] = useState({ current: false, next: false, confirm: false });

  const setField = (f) => (v) => {
    setForm((prev) => ({ ...prev, [f]: v }));
    setErrors((prev) => ({ ...prev, [f]: null }));
  };
  const toggleShow = (f) => setShow((s) => ({ ...s, [f]: !s[f] }));

  const validate = () => {
    const e = {};
    if (!form.current) e.current = t("profile.current_pin") + " required";
    if (!/^\d{4,6}$/.test(form.next)) e.next = "New PIN must be 4–6 digits";
    if (form.next === form.current) e.next = "New PIN must differ from current";
    if (form.next !== form.confirm) e.confirm = "PINs do not match";
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validate()) return;
    setLoading(true);
    try {
      await authApi.changePassword(form.current, form.next);
      setPinDone(true);
      setForm({ current: "", next: "", confirm: "" });
      setTimeout(() => { setShowPinForm(false); setPinDone(false); }, 2500);
    } catch (err) {
      const msg = getApiError(err);
      if (msg.toLowerCase().includes("current") || msg.toLowerCase().includes("incorrect")) {
        setErrors({ current: "Incorrect PIN — try again" });
      } else {
        toast.error(msg);
      }
    } finally {
      setLoading(false);
    }
  };

  const cancelPinForm = () => {
    setShowPinForm(false);
    setPinDone(false);
    setErrors({});
    setForm({ current: "", next: "", confirm: "" });
  };

  const handleLogout = async () => {
    try {
      const at = localStorage.getItem("access_token");
      const rt = localStorage.getItem("refresh_token");
      if (at) await authApi.logout(at).catch(() => {});
      if (rt) await authApi.logout(rt).catch(() => {});
    } finally {
      logout();
      toast.success("Logged out.");
      router.push("/login");
    }
  };

  return (
    <div className="p-4 space-y-4 pb-8">

      {/* ── Header ── */}
      <div className="flex items-center gap-3 pt-1">
        <button
          onClick={() => router.back()}
          className="w-8 h-8 flex items-center justify-center rounded-xl bg-slate-100 hover:bg-slate-200 transition-colors"
        >
          <ArrowLeft size={16} className="text-slate-600" />
        </button>
        <div>
          <h1 className="text-xl font-bold text-slate-800">{t("profile.title")}</h1>
          <p className="text-xs text-slate-400 mt-0.5">Account & security</p>
        </div>
      </div>

      {/* ── Avatar card ── */}
      <div className="bg-white rounded-2xl border border-slate-200 p-5 flex items-center gap-4">
        <div className="w-16 h-16 bg-blue-700 rounded-2xl flex items-center justify-center shrink-0 shadow-inner">
          <span className="text-2xl font-bold text-white select-none">
            {getInitials(user?.name || "?")}
          </span>
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-lg font-bold text-slate-800 truncate">{user?.name}</p>
          <div className="flex items-center gap-1.5 mt-0.5">
            <Phone size={11} className="text-slate-400 shrink-0" />
            <p className="text-sm text-slate-500">+91 {user?.phone || "—"}</p>
          </div>
          <span className="inline-block mt-2 text-[11px] font-bold text-blue-700 bg-blue-50 px-2.5 py-0.5 rounded-full tracking-wide">
            CLIENT
          </span>
        </div>
      </div>

      {/* ── Business info ── */}
      <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
        <div className="px-4 py-2.5 border-b border-slate-100">
          <p className="text-[11px] font-bold text-slate-400 uppercase tracking-widest">Business</p>
        </div>
        <div className="divide-y divide-slate-100">
          <InfoRow icon={Building2} label="Business Name" value={org?.name} />
          <InfoRow icon={User}      label="Managed by CA" value={org?.ca_firm || org?.owner_name} />
        </div>
      </div>

      {/* ── Quick links ── */}
      <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
        <div className="px-4 py-2.5 border-b border-slate-100">
          <p className="text-[11px] font-bold text-slate-400 uppercase tracking-widest">Reports</p>
        </div>
        <div className="divide-y divide-slate-100">
          <LinkRow
            icon={Star}
            label={t("score.title")}
            sub="View and share your compliance grade"
            href="/score"
            iconBg="bg-blue-50"
            iconColor="text-blue-600"
          />
          <LinkRow
            icon={FileText}
            label={t("report.title")}
            sub="Download year's financial summary as PDF"
            href="/annual-report"
            iconBg="bg-indigo-50"
            iconColor="text-indigo-600"
          />
          <LinkRow
            icon={Receipt}
            label="GST Invoice Generator"
            sub="Create print-ready GST invoices"
            href="/invoice"
            iconBg="bg-emerald-50"
            iconColor="text-emerald-600"
          />
          <LinkRow
            icon={Upload}
            label="Import Bank Statement"
            sub="Auto-create transactions from CSV"
            href="/import-statement"
            iconBg="bg-violet-50"
            iconColor="text-violet-600"
          />
        </div>
      </div>

      {/* ── Security: PIN change ── */}
      <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
        <div className="px-4 py-2.5 border-b border-slate-100">
          <p className="text-[11px] font-bold text-slate-400 uppercase tracking-widest">Security</p>
        </div>

        {!showPinForm ? (
          <button
            onClick={() => setShowPinForm(true)}
            className="w-full flex items-center gap-3 px-4 py-4 hover:bg-slate-50 active:bg-slate-100 transition-colors text-left"
          >
            <div className="w-9 h-9 bg-slate-100 rounded-xl flex items-center justify-center shrink-0">
              <Lock size={16} className="text-slate-600" />
            </div>
            <div className="flex-1">
              <p className="text-sm font-semibold text-slate-700">{t("profile.change_pin")}</p>
              <p className="text-xs text-slate-400 mt-0.5">Update your 4–6 digit login PIN</p>
            </div>
            <Shield size={14} className="text-slate-300 shrink-0" />
          </button>
        ) : (
          <div className="p-4">
            {pinDone ? (
              <div className="flex items-center gap-3 py-5 justify-center">
                <CheckCircle2 size={28} className="text-green-500 shrink-0" />
                <div>
                  <p className="text-base font-bold text-green-700">PIN changed!</p>
                  <p className="text-xs text-green-600 mt-0.5">Use your new PIN next time you log in.</p>
                </div>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-4">
                <PINField
                  label={t("profile.current_pin")}
                  value={form.current}
                  show={show.current}
                  onToggle={() => toggleShow("current")}
                  onChange={setField("current")}
                  error={errors.current}
                  placeholder="Your existing PIN"
                />
                <PINField
                  label={t("profile.new_pin")}
                  value={form.next}
                  show={show.next}
                  onToggle={() => toggleShow("next")}
                  onChange={setField("next")}
                  error={errors.next}
                  placeholder="4–6 digits"
                />
                <PINField
                  label={t("profile.confirm_pin")}
                  value={form.confirm}
                  show={show.confirm}
                  onToggle={() => toggleShow("confirm")}
                  onChange={setField("confirm")}
                  error={errors.confirm}
                  placeholder="Re-enter new PIN"
                />
                <div className="flex gap-2 pt-1">
                  <button type="button" onClick={cancelPinForm} className="btn-outline flex-1">
                    {t("common.cancel")}
                  </button>
                  <button type="submit" disabled={loading} className="btn-primary flex-1">
                    {loading
                      ? <><Loader2 size={14} className="animate-spin" /> Saving…</>
                      : t("profile.save")
                    }
                  </button>
                </div>
              </form>
            )}
          </div>
        )}
      </div>

      {/* ── Preferences: language toggle ── */}
      <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
        <div className="px-4 py-2.5 border-b border-slate-100">
          <p className="text-[11px] font-bold text-slate-400 uppercase tracking-widest">Preferences</p>
        </div>
        <LanguageToggle lang={lang} setLang={setLang} t={t} />
      </div>

      {/* ── Logout ── */}
      <button
        onClick={handleLogout}
        className="w-full flex items-center gap-3 bg-white rounded-2xl border border-red-100 px-4 py-4 hover:bg-red-50 active:bg-red-100 transition-colors text-left"
      >
        <div className="w-9 h-9 bg-red-50 rounded-xl flex items-center justify-center shrink-0">
          <LogOut size={16} className="text-red-500" />
        </div>
        <p className="text-sm font-semibold text-red-600">{t("profile.logout")}</p>
      </button>

      {/* ── Version ── */}
      <p className="text-xs text-center text-slate-300 pb-2">BharatCompliance v2.0</p>
    </div>
  );
}
