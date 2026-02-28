"use client";

import { useState, useMemo, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Plus, Search, X, Copy, Check, ExternalLink,
  Users, AlertTriangle, Clock, UserCheck, ChevronRight,
  Phone, Building2, QrCode, Upload, FileText, CheckCircle2, XCircle,
} from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";
import { clientsApi } from "@/lib/api/clients";
import { getApiError } from "@/lib/api/client";
import { COMPLIANCE_COLORS } from "@/constants";
import { formatDate, timeAgo, getInitials } from "@/lib/utils";
import apiClient from "@/lib/api/client";

// ── Constants ────────────────────────────────────────────────────────
const BUSINESS_TYPES = [
  { value: "food",           label: "Food & Beverages" },
  { value: "retail",         label: "Retail" },
  { value: "service",        label: "Service" },
  { value: "manufacturing",  label: "Manufacturing" },
  { value: "agriculture",    label: "Agriculture" },
  { value: "transport",      label: "Transport" },
  { value: "construction",   label: "Construction" },
  { value: "healthcare",     label: "Healthcare" },
  { value: "education",      label: "Education" },
  { value: "other",          label: "Other" },
];

const INDIA_STATES = [
  "Andhra Pradesh","Arunachal Pradesh","Assam","Bihar","Chhattisgarh",
  "Goa","Gujarat","Haryana","Himachal Pradesh","Jharkhand","Karnataka",
  "Kerala","Madhya Pradesh","Maharashtra","Manipur","Meghalaya","Mizoram",
  "Nagaland","Odisha","Punjab","Rajasthan","Sikkim","Tamil Nadu","Telangana",
  "Tripura","Uttar Pradesh","Uttarakhand","West Bengal",
  "Andaman and Nicobar Islands","Chandigarh","Dadra and Nagar Haveli",
  "Daman and Diu","Delhi","Jammu and Kashmir","Ladakh","Lakshadweep","Puducherry",
];

const FILTERS = [
  { key: "all",     label: "All",           icon: Users },
  { key: "red",     label: "Urgent",        icon: AlertTriangle },
  { key: "yellow",  label: "Needs Attention", icon: Clock },
  { key: "green",   label: "Active",        icon: UserCheck },
  { key: "pending", label: "Pending Invite", icon: QrCode },
];

const EMPTY_FORM = {
  name: "", business_type: "", state: "", gstin: "",
  pan: "", expected_turnover: "", phone: "", whatsapp_phone: "",
};

// ── Helpers ──────────────────────────────────────────────────────────

function validate(form) {
  const errs = {};
  if (!form.name.trim()) errs.name = "Business name is required.";
  else if (form.name.trim().length < 2) errs.name = "Name must be at least 2 characters.";
  if (form.gstin && !/^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$/.test(form.gstin.toUpperCase()))
    errs.gstin = "Invalid GSTIN format.";
  if (form.pan && !/^[A-Z]{5}[0-9]{4}[A-Z]$/.test(form.pan.toUpperCase()))
    errs.pan = "Invalid PAN format (e.g. AAAAA0000A).";
  if (form.phone && !/^[6-9]\d{9}$/.test(form.phone.replace(/\D/g, "")))
    errs.phone = "Enter a valid 10-digit Indian mobile number.";
  if (form.whatsapp_phone && !/^[6-9]\d{9}$/.test(form.whatsapp_phone.replace(/\D/g, "")))
    errs.whatsapp_phone = "Enter a valid 10-digit WhatsApp number.";
  if (form.expected_turnover && (isNaN(Number(form.expected_turnover)) || Number(form.expected_turnover) < 0))
    errs.expected_turnover = "Enter a valid positive number.";
  return errs;
}

// ── Sub-components ────────────────────────────────────────────────────

function StatBar({ clients }) {
  const counts = useMemo(() => ({
    total:   clients.length,
    active:  clients.filter((c) => c.invite_status === "active").length,
    red:     clients.filter((c) => c.compliance_color === "red").length,
    yellow:  clients.filter((c) => c.compliance_color === "yellow").length,
    green:   clients.filter((c) => c.compliance_color === "green").length,
  }), [clients]);

  return (
    <div className="grid grid-cols-4 gap-3 mb-5">
      {[
        { label: "Total Clients", value: counts.total,  color: "bg-slate-100 text-slate-700" },
        { label: "Urgent",        value: counts.red,    color: "bg-red-50 text-red-700" },
        { label: "Attention",     value: counts.yellow, color: "bg-yellow-50 text-yellow-700" },
        { label: "Active",        value: counts.green,  color: "bg-green-50 text-green-700" },
      ].map(({ label, value, color }) => (
        <div key={label} className={`rounded-xl p-3 ${color}`}>
          <p className="text-2xl font-bold">{value}</p>
          <p className="text-xs font-medium opacity-70 mt-0.5">{label}</p>
        </div>
      ))}
    </div>
  );
}

function ClientRow({ client }) {
  const c = COMPLIANCE_COLORS[client.compliance_color] || COMPLIANCE_COLORS.green;
  const isPending = client.invite_status !== "active";
  return (
    <Link
      href={`/clients/${client.id}`}
      className="flex items-center gap-4 px-5 py-4 hover:bg-slate-50 transition-colors group"
    >
      {/* Avatar */}
      <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center shrink-0">
        <span className="text-sm font-bold text-blue-700">{getInitials(client.name)}</span>
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-slate-800 truncate">{client.name}</span>
          {isPending && (
            <span className="text-[10px] font-medium bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded-full shrink-0">
              Invite Pending
            </span>
          )}
        </div>
        <div className="flex items-center gap-3 mt-0.5">
          {client.business_type && (
            <span className="text-xs text-slate-400 capitalize">{client.business_type}</span>
          )}
          {client.phone && (
            <span className="text-xs text-slate-400">{client.phone}</span>
          )}
        </div>
      </div>

      {/* Right side */}
      <div className="flex items-center gap-3 shrink-0">
        <div className="text-right hidden sm:block">
          <div className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-1 rounded-full ${c.bg} ${c.text}`}>
            <span className={`w-1.5 h-1.5 rounded-full ${c.dot}`} />
            {client.compliance_score != null ? `${Math.round(client.compliance_score)}%` : c.label}
          </div>
          {client.days_since_last_entry != null && (
            <p className="text-[10px] text-slate-400 mt-1">
              {client.days_since_last_entry === 0
                ? "Entry today"
                : `${client.days_since_last_entry}d since last entry`}
            </p>
          )}
        </div>
        <ChevronRight size={16} className="text-slate-300 group-hover:text-slate-500 transition-colors" />
      </div>
    </Link>
  );
}

function FieldError({ msg }) {
  if (!msg) return null;
  return <p className="text-xs text-red-500 mt-1">{msg}</p>;
}

function FormField({ label, error, required, children }) {
  return (
    <div>
      <label className="block text-sm font-medium text-slate-700 mb-1">
        {label}{required && <span className="text-red-500 ml-0.5">*</span>}
      </label>
      {children}
      <FieldError msg={error} />
    </div>
  );
}

// ── CSV Import Template ───────────────────────────────────────────────

const CSV_TEMPLATE = `name,business_type,state,phone,gstin,pan,expected_turnover,whatsapp_phone
Ram Prasad Tea Stall,food,Maharashtra,9876543210,,,200000,9876543210
Priya Fashion Boutique,retail,Gujarat,8765432109,,,500000,
Suresh Transport Co,transport,Rajasthan,7654321098,,,1500000,7654321098
`;

function downloadCsvTemplate() {
  const blob = new Blob([CSV_TEMPLATE], { type: "text/csv" });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement("a");
  a.href     = url;
  a.download = "clients_import_template.csv";
  a.click();
  URL.revokeObjectURL(url);
}

// ── CSV Import Modal ──────────────────────────────────────────────────

function CsvImportModal({ onClose, onDone }) {
  const fileRef  = useRef(null);
  const [file,   setFile]   = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const qc = useQueryClient();

  const handleFileChange = (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    if (!f.name.toLowerCase().endsWith(".csv")) { toast.error("Only CSV files accepted."); return; }
    if (f.size > 600_000) { toast.error("File too large. Max 500 KB."); return; }
    setFile(f);
    setResult(null);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    const f = e.dataTransfer.files?.[0];
    if (f) handleFileChange({ target: { files: [f] } });
  };

  const handleUpload = async () => {
    if (!file) { toast.error("Select a CSV file first."); return; }
    setLoading(true);
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await apiClient.post("/clients/import", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      const data = res.data.data;
      setResult(data);
      if (data.created_count > 0) {
        qc.invalidateQueries({ queryKey: ["ca-clients"] });
        toast.success(`${data.created_count} client${data.created_count !== 1 ? "s" : ""} imported!`);
      } else {
        toast.warning("No clients could be imported. Check skipped rows.");
      }
    } catch (err) {
      const msg = err.response?.data?.error;
      toast.error(typeof msg === "string" ? msg : "Upload failed. Try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/40 backdrop-blur-sm">
      <div className="bg-white w-full sm:max-w-lg sm:rounded-2xl rounded-t-2xl max-h-[90vh] flex flex-col shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 shrink-0">
          <div>
            <h2 className="text-base font-bold text-slate-800">Import Clients from CSV</h2>
            <p className="text-xs text-slate-400 mt-0.5">Bulk-add up to 200 clients in one upload</p>
          </div>
          <button onClick={onClose} className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-slate-100 text-slate-500">
            <X size={18} />
          </button>
        </div>

        <div className="overflow-y-auto flex-1 px-6 py-4 space-y-4">
          {/* Template download */}
          <div className="bg-slate-50 rounded-xl p-3 flex items-center justify-between">
            <div className="text-xs text-slate-600">
              <p className="font-semibold mb-0.5">Need the template?</p>
              <p className="text-slate-400">Required columns: <code className="bg-slate-200 px-1 rounded">name</code></p>
            </div>
            <button
              onClick={downloadCsvTemplate}
              className="flex items-center gap-1.5 text-xs font-semibold text-blue-600 hover:text-blue-800 border border-blue-200 rounded-lg px-3 py-1.5 hover:bg-blue-50"
            >
              <FileText size={13} /> Download Template
            </button>
          </div>

          {/* Drop zone */}
          <div
            onDrop={handleDrop}
            onDragOver={(e) => e.preventDefault()}
            onClick={() => fileRef.current?.click()}
            className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-colors
              ${file ? "border-green-400 bg-green-50" : "border-slate-300 hover:border-blue-400 hover:bg-blue-50"}`}
          >
            <input ref={fileRef} type="file" accept=".csv" className="hidden" onChange={handleFileChange} />
            {file ? (
              <div className="space-y-1">
                <CheckCircle2 size={28} className="text-green-500 mx-auto" />
                <p className="text-sm font-semibold text-green-700">{file.name}</p>
                <p className="text-xs text-green-500">{(file.size / 1024).toFixed(1)} KB · Click to change</p>
              </div>
            ) : (
              <div className="space-y-2">
                <Upload size={28} className="text-slate-400 mx-auto" />
                <p className="text-sm font-semibold text-slate-700">Drop CSV here or click to browse</p>
                <p className="text-xs text-slate-400">Max 500 KB · up to 200 rows</p>
              </div>
            )}
          </div>

          {/* Results */}
          {result && (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-green-50 border border-green-200 rounded-xl p-3 text-center">
                  <p className="text-xl font-bold text-green-700">{result.created_count}</p>
                  <p className="text-xs text-green-600 mt-0.5">Clients Created</p>
                </div>
                <div className={`border rounded-xl p-3 text-center ${result.skipped_count > 0 ? "bg-amber-50 border-amber-200" : "bg-slate-50 border-slate-200"}`}>
                  <p className={`text-xl font-bold ${result.skipped_count > 0 ? "text-amber-700" : "text-slate-500"}`}>{result.skipped_count}</p>
                  <p className={`text-xs mt-0.5 ${result.skipped_count > 0 ? "text-amber-600" : "text-slate-400"}`}>Skipped</p>
                </div>
              </div>

              {result.skipped.length > 0 && (
                <div className="bg-amber-50 border border-amber-200 rounded-xl p-3">
                  <p className="text-xs font-semibold text-amber-700 mb-2">Skipped rows:</p>
                  <div className="space-y-1 max-h-32 overflow-y-auto">
                    {result.skipped.map((s, i) => (
                      <div key={i} className="text-xs text-amber-600 flex gap-2">
                        <span className="font-medium">Row {s.row}:</span>
                        <span>{s.name && `${s.name} — `}{s.reason}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-slate-100 flex gap-3 shrink-0">
          <button onClick={onClose} className="btn-outline flex-1">
            {result ? "Close" : "Cancel"}
          </button>
          {!result && (
            <button
              onClick={handleUpload}
              disabled={!file || loading}
              className="btn-primary flex-1"
            >
              {loading ? "Importing…" : "Import Clients"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Add Client Modal ──────────────────────────────────────────────────

function AddClientModal({ onClose, onCreated }) {
  const [form,   setForm]   = useState(EMPTY_FORM);
  const [errors, setErrors] = useState({});
  const qc = useQueryClient();

  const mutation = useMutation({
    mutationFn: (data) => clientsApi.create(data),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ["ca-clients"] });
      onCreated(res.data.data);
    },
    onError: (err) => {
      const msg = getApiError(err);
      if (typeof msg === "object") setErrors(msg);
      else toast.error(msg);
    },
  });

  const set = (field) => (e) => setForm((f) => ({ ...f, [field]: e.target.value }));

  const handleSubmit = (e) => {
    e.preventDefault();
    const errs = validate(form);
    if (Object.keys(errs).length) { setErrors(errs); return; }
    setErrors({});

    const payload = { name: form.name.trim() };
    if (form.business_type) payload.business_type = form.business_type;
    if (form.state)          payload.state          = form.state;
    if (form.gstin)          payload.gstin          = form.gstin.toUpperCase();
    if (form.pan)            payload.pan            = form.pan.toUpperCase();
    if (form.expected_turnover) payload.expected_turnover = Number(form.expected_turnover);
    if (form.phone)          payload.phone          = form.phone.replace(/\D/g, "");
    if (form.whatsapp_phone) payload.whatsapp_phone = form.whatsapp_phone.replace(/\D/g, "");

    mutation.mutate(payload);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/40 backdrop-blur-sm">
      <div className="bg-white w-full sm:max-w-lg sm:rounded-2xl rounded-t-2xl max-h-[92vh] flex flex-col shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 shrink-0">
          <div>
            <h2 className="text-base font-bold text-slate-800">Add New Client</h2>
            <p className="text-xs text-slate-400 mt-0.5">Fill in business details to generate an invite</p>
          </div>
          <button onClick={onClose} className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-slate-100 text-slate-500">
            <X size={18} />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="overflow-y-auto flex-1 px-6 py-4 space-y-4">
          {/* Name */}
          <FormField label="Business Name" required error={errors.name}>
            <input
              value={form.name}
              onChange={set("name")}
              placeholder="Ram Prasad Tea Stall"
              className={`input-base ${errors.name ? "error" : ""}`}
            />
          </FormField>

          {/* Type + State */}
          <div className="grid grid-cols-2 gap-3">
            <FormField label="Business Type" error={errors.business_type}>
              <select value={form.business_type} onChange={set("business_type")} className="input-base">
                <option value="">Select type</option>
                {BUSINESS_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </FormField>
            <FormField label="State" error={errors.state}>
              <select value={form.state} onChange={set("state")} className="input-base">
                <option value="">Select state</option>
                {INDIA_STATES.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </FormField>
          </div>

          {/* GSTIN + PAN */}
          <div className="grid grid-cols-2 gap-3">
            <FormField label="GSTIN" error={errors.gstin}>
              <input
                value={form.gstin}
                onChange={set("gstin")}
                placeholder="27AAAAA0000A1Z5"
                maxLength={15}
                className={`input-base uppercase ${errors.gstin ? "error" : ""}`}
              />
            </FormField>
            <FormField label="PAN" error={errors.pan}>
              <input
                value={form.pan}
                onChange={set("pan")}
                placeholder="AAAAA0000A"
                maxLength={10}
                className={`input-base uppercase ${errors.pan ? "error" : ""}`}
              />
            </FormField>
          </div>

          {/* Expected Turnover */}
          <FormField label="Expected Annual Turnover (₹)" error={errors.expected_turnover}>
            <input
              type="number"
              value={form.expected_turnover}
              onChange={set("expected_turnover")}
              placeholder="500000"
              min={0}
              className={`input-base ${errors.expected_turnover ? "error" : ""}`}
            />
          </FormField>

          {/* Phone + WhatsApp */}
          <div className="grid grid-cols-2 gap-3">
            <FormField label="Phone" error={errors.phone}>
              <input
                type="tel"
                value={form.phone}
                onChange={set("phone")}
                placeholder="9876543210"
                maxLength={10}
                className={`input-base ${errors.phone ? "error" : ""}`}
              />
            </FormField>
            <FormField label="WhatsApp" error={errors.whatsapp_phone}>
              <input
                type="tel"
                value={form.whatsapp_phone}
                onChange={set("whatsapp_phone")}
                placeholder="9876543210"
                maxLength={10}
                className={`input-base ${errors.whatsapp_phone ? "error" : ""}`}
              />
            </FormField>
          </div>
        </form>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-slate-100 flex gap-3 shrink-0">
          <button onClick={onClose} className="btn-outline flex-1">Cancel</button>
          <button
            onClick={handleSubmit}
            disabled={mutation.isPending}
            className="btn-primary flex-1"
          >
            {mutation.isPending ? "Creating…" : "Create & Get Invite"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Invite Success Panel ──────────────────────────────────────────────

function InvitePanel({ data, onClose }) {
  const [copied, setCopied] = useState(false);
  const inviteUrl = typeof window !== "undefined"
    ? `${window.location.origin}/invite/${data.client.invite_code}`
    : data.invite_url || "";

  const copy = () => {
    navigator.clipboard.writeText(inviteUrl);
    setCopied(true);
    toast.success("Link copied!");
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/40 backdrop-blur-sm">
      <div className="bg-white w-full sm:max-w-md sm:rounded-2xl rounded-t-2xl p-6 shadow-2xl">
        {/* Success header */}
        <div className="text-center mb-5">
          <div className="w-14 h-14 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-3">
            <UserCheck size={26} className="text-green-600" />
          </div>
          <h2 className="text-lg font-bold text-slate-800">Client Added!</h2>
          <p className="text-sm text-slate-500 mt-1">
            Share this invite with <span className="font-semibold text-slate-700">{data.client.name}</span>
          </p>
        </div>

        {/* QR Code */}
        {data.qr_svg && (
          <div
            className="mx-auto w-40 h-40 mb-4 flex items-center justify-center"
            dangerouslySetInnerHTML={{ __html: data.qr_svg }}
          />
        )}

        {/* Invite link */}
        <div className="bg-slate-50 rounded-xl px-4 py-3 flex items-center gap-3 mb-4">
          <span className="flex-1 text-xs text-slate-600 break-all">{inviteUrl}</span>
          <button
            onClick={copy}
            className="shrink-0 w-8 h-8 flex items-center justify-center rounded-lg bg-blue-700 text-white hover:bg-blue-800 transition-colors"
          >
            {copied ? <Check size={14} /> : <Copy size={14} />}
          </button>
        </div>

        {/* Expiry notice */}
        <p className="text-xs text-slate-400 text-center mb-4">
          Invite expires on{" "}
          <span className="font-medium text-slate-600">
            {formatDate(data.client.invite_expires_at)}
          </span>
        </p>

        <div className="flex gap-3">
          <Link
            href={`/clients/${data.client.id}`}
            className="btn-outline flex-1 text-center"
            onClick={onClose}
          >
            View Client
          </Link>
          <button onClick={onClose} className="btn-primary flex-1">Done</button>
        </div>
      </div>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────

export default function ClientsPage() {
  const [search,      setSearch]      = useState("");
  const [filter,      setFilter]      = useState("all");
  const [showAdd,     setShowAdd]     = useState(false);
  const [showImport,  setShowImport]  = useState(false);
  const [inviteData,  setInviteData]  = useState(null);

  const { data, isLoading } = useQuery({
    queryKey: ["ca-clients"],
    queryFn: () => clientsApi.list().then((r) => r.data.data),
  });

  const clients = data?.clients || [];

  const filtered = useMemo(() => {
    let list = clients;
    if (filter === "pending") list = list.filter((c) => c.invite_status !== "active");
    else if (filter !== "all") list = list.filter((c) => c.compliance_color === filter);
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter(
        (c) =>
          c.name.toLowerCase().includes(q) ||
          c.phone?.includes(q) ||
          c.business_type?.toLowerCase().includes(q),
      );
    }
    return list;
  }, [clients, filter, search]);

  return (
    <div className="p-5">
      {/* Page header */}
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-xl font-bold text-slate-800">Clients</h1>
          <p className="text-sm text-slate-400 mt-0.5">
            {isLoading ? "Loading…" : `${clients.length} client${clients.length !== 1 ? "s" : ""}`}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowImport(true)}
            className="btn-outline gap-1.5 text-sm"
            title="Import clients from CSV"
          >
            <Upload size={14} />
            Import CSV
          </button>
          <button
            onClick={() => setShowAdd(true)}
            className="btn-primary gap-2"
          >
            <Plus size={16} />
            Add Client
          </button>
        </div>
      </div>

      {/* Stats */}
      {!isLoading && clients.length > 0 && <StatBar clients={clients} />}

      {/* Search */}
      <div className="relative mb-4">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
        <input
          type="search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search clients…"
          className="input-base pl-9"
        />
      </div>

      {/* Filter pills */}
      <div className="flex gap-2 mb-4 overflow-x-auto pb-1 scrollbar-hide">
        {FILTERS.map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setFilter(key)}
            className={`shrink-0 text-xs font-medium px-3 py-1.5 rounded-full border transition-colors ${
              filter === key
                ? "bg-blue-700 text-white border-blue-700"
                : "bg-white text-slate-600 border-slate-200 hover:border-blue-300"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Client list */}
      <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
        {isLoading ? (
          <div className="divide-y divide-slate-100">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="px-5 py-4 flex items-center gap-4 animate-pulse">
                <div className="w-10 h-10 rounded-full bg-slate-200" />
                <div className="flex-1 space-y-2">
                  <div className="h-3 bg-slate-200 rounded w-40" />
                  <div className="h-2 bg-slate-100 rounded w-24" />
                </div>
                <div className="h-6 w-16 bg-slate-100 rounded-full" />
              </div>
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="py-16 text-center">
            <Users size={36} className="mx-auto text-slate-300 mb-3" />
            <p className="text-sm font-medium text-slate-500">
              {search || filter !== "all" ? "No clients match your filter" : "No clients yet"}
            </p>
            {!search && filter === "all" && (
              <p className="text-xs text-slate-400 mt-1">
                Click "Add Client" to add your first business.
              </p>
            )}
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {filtered.map((c) => <ClientRow key={c.id} client={c} />)}
          </div>
        )}
      </div>

      {/* Modals */}
      {showAdd && (
        <AddClientModal
          onClose={() => setShowAdd(false)}
          onCreated={(res) => { setShowAdd(false); setInviteData(res); }}
        />
      )}
      {showImport && (
        <CsvImportModal
          onClose={() => setShowImport(false)}
          onDone={() => setShowImport(false)}
        />
      )}
      {inviteData && (
        <InvitePanel
          data={inviteData}
          onClose={() => setInviteData(null)}
        />
      )}
    </div>
  );
}
