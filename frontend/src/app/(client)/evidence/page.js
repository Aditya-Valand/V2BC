"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Upload, Camera, Image, CheckCircle2, XCircle, Clock,
  Loader2, AlertTriangle, FileText, IndianRupee, Calendar,
  Store, ShieldCheck, Trash2, ChevronDown, ChevronUp,
} from "lucide-react";
import { toast } from "sonner";
import { evidenceApi } from "@/lib/api/evidence";
import { getApiError } from "@/lib/api/client";
import { EVIDENCE_STRENGTH } from "@/constants";
import { formatINR, formatDate, timeAgo } from "@/lib/utils";
import useAuthStore from "@/store/authStore";

// ── OCR Status pill ──────────────────────────────────────────────────

function OcrStatusPill({ status }) {
  const map = {
    pending:    { label: "Scanning…",    cls: "bg-blue-100 text-blue-700",   icon: Loader2,       spin: true  },
    processing: { label: "Processing…", cls: "bg-blue-100 text-blue-700",   icon: Loader2,       spin: true  },
    success:    { label: "Scanned",      cls: "bg-green-100 text-green-700", icon: CheckCircle2,  spin: false },
    failed:     { label: "Scan Failed",  cls: "bg-red-100 text-red-700",     icon: XCircle,       spin: false },
  };
  const s = map[status] || map.pending;
  const Icon = s.icon;
  return (
    <span className={`inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full ${s.cls}`}>
      <Icon size={12} className={s.spin ? "animate-spin" : ""} />
      {s.label}
    </span>
  );
}

// ── Quality score bar ────────────────────────────────────────────────

function QualityBar({ score, status }) {
  const pct = Math.min(100, Math.round(score || 0));
  const color = status === "good"
    ? "bg-green-500"
    : status === "low_quality"
    ? "bg-yellow-400"
    : "bg-red-500";
  return (
    <div>
      <div className="flex justify-between mb-1">
        <span className="text-xs text-slate-500">Photo Quality</span>
        <span className={`text-xs font-semibold ${pct >= 70 ? "text-green-700" : pct >= 40 ? "text-yellow-700" : "text-red-700"}`}>
          {pct}%
        </span>
      </div>
      <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all duration-500 ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

// ── Uploaded evidence result card ────────────────────────────────────

function EvidenceResultCard({ evidenceId, onDismiss }) {
  const [expanded, setExpanded] = useState(true);

  const { data, isLoading } = useQuery({
    queryKey: ["evidence", evidenceId],
    queryFn: () => evidenceApi.get(evidenceId).then((r) => r.data.data),
    refetchInterval: (query) => {
      const status = query.state.data?.ocr_status;
      if (status === "success" || status === "failed") return false;
      return 2500; // poll every 2.5s while pending/processing
    },
    staleTime: 0,
  });

  if (isLoading) {
    return (
      <div className="bg-white rounded-2xl border border-slate-200 p-5 animate-pulse">
        <div className="h-4 bg-slate-200 rounded w-1/2 mb-3" />
        <div className="h-24 bg-slate-100 rounded-xl" />
      </div>
    );
  }

  if (!data) return null;

  const strength = EVIDENCE_STRENGTH[data.strength] || EVIDENCE_STRENGTH.medium;
  const isPending = data.ocr_status === "pending" || data.ocr_status === "processing";
  const isSuccess = data.ocr_status === "success";

  return (
    <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100">
        <div className="flex items-center gap-2">
          <OcrStatusPill status={data.ocr_status} />
          <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${strength.bg} ${strength.text}`}>
            {strength.label} Evidence
          </span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setExpanded((x) => !x)}
            className="p-1 text-slate-400 hover:text-slate-600"
          >
            {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>
          <button
            onClick={onDismiss}
            className="p-1 text-slate-400 hover:text-red-500 transition-colors"
          >
            <Trash2 size={15} />
          </button>
        </div>
      </div>

      {expanded && (
        <div className="p-4 space-y-4">
          {/* Photo preview */}
          {data.thumbnail_url && (
            <div className="relative">
              <img
                src={data.thumbnail_url}
                alt="Receipt"
                className="w-full max-h-48 object-cover rounded-xl bg-slate-100"
              />
            </div>
          )}

          {/* Quality bar */}
          <QualityBar score={data.quality_score} status={data.quality_status} />

          {/* OCR results */}
          {isSuccess && (
            <div className="bg-green-50 rounded-xl p-3 space-y-2">
              <p className="text-xs font-bold text-green-800 mb-2 flex items-center gap-1.5">
                <ShieldCheck size={12} /> Extracted Details
              </p>
              <div className="grid grid-cols-2 gap-2">
                {data.ocr_amount != null && (
                  <div className="flex items-start gap-2">
                    <IndianRupee size={13} className="text-green-600 mt-0.5 shrink-0" />
                    <div>
                      <p className="text-[10px] text-green-700 font-medium">Amount</p>
                      <p className="text-sm font-bold text-green-900">{formatINR(data.ocr_amount)}</p>
                    </div>
                  </div>
                )}
                {data.ocr_date && (
                  <div className="flex items-start gap-2">
                    <Calendar size={13} className="text-green-600 mt-0.5 shrink-0" />
                    <div>
                      <p className="text-[10px] text-green-700 font-medium">Date</p>
                      <p className="text-sm font-bold text-green-900">{formatDate(data.ocr_date)}</p>
                    </div>
                  </div>
                )}
                {data.ocr_vendor_name && (
                  <div className="flex items-start gap-2 col-span-2">
                    <Store size={13} className="text-green-600 mt-0.5 shrink-0" />
                    <div>
                      <p className="text-[10px] text-green-700 font-medium">Vendor</p>
                      <p className="text-sm font-bold text-green-900">{data.ocr_vendor_name}</p>
                    </div>
                  </div>
                )}
                {data.ocr_document_type && (
                  <div className="flex items-start gap-2">
                    <FileText size={13} className="text-green-600 mt-0.5 shrink-0" />
                    <div>
                      <p className="text-[10px] text-green-700 font-medium">Type</p>
                      <p className="text-sm font-bold text-green-900 capitalize">{data.ocr_document_type}</p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {data.ocr_status === "failed" && (
            <div className="bg-red-50 rounded-xl p-3 flex items-start gap-2">
              <XCircle size={14} className="text-red-500 mt-0.5 shrink-0" />
              <p className="text-xs text-red-700">
                Could not extract details from this photo. You can still save it as supporting evidence.
              </p>
            </div>
          )}

          {isPending && (
            <div className="bg-blue-50 rounded-xl p-3 flex items-center gap-2">
              <Loader2 size={14} className="text-blue-600 animate-spin shrink-0" />
              <p className="text-xs text-blue-700">
                AI is scanning your receipt for amount, date, and vendor details…
              </p>
            </div>
          )}

          {data.quality_status === "low_quality" && (
            <div className="bg-yellow-50 rounded-xl p-3 flex items-start gap-2">
              <AlertTriangle size={13} className="text-yellow-600 mt-0.5 shrink-0" />
              <p className="text-xs text-yellow-800">
                Photo quality is low. For better OCR results, try retaking in good lighting.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Recent evidence list ─────────────────────────────────────────────

function RecentEvidenceList({ businessId }) {
  const { data, isLoading } = useQuery({
    queryKey: ["evidence-list", businessId],
    queryFn: () => evidenceApi.listForClient(businessId, { per_page: 10 }).then((r) => r.data.data),
    enabled: !!businessId,
  });

  if (isLoading) {
    return (
      <div className="space-y-2">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="h-14 bg-slate-100 rounded-xl animate-pulse" />
        ))}
      </div>
    );
  }

  const items = data?.evidence || [];
  if (items.length === 0) return null;

  return (
    <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
      <p className="px-4 py-3 text-sm font-semibold text-slate-700 border-b border-slate-100">
        Recent Receipts
      </p>
      <div className="divide-y divide-slate-100">
        {items.map((ev) => {
          const strength = EVIDENCE_STRENGTH[ev.strength] || EVIDENCE_STRENGTH.medium;
          return (
            <div key={ev.id} className="flex items-center gap-3 px-4 py-3">
              {/* Thumbnail */}
              <div className="w-10 h-10 rounded-lg bg-slate-100 overflow-hidden shrink-0">
                {ev.thumbnail_url ? (
                  <img src={ev.thumbnail_url} alt="Receipt" className="w-full h-full object-cover" />
                ) : (
                  <div className="w-full h-full flex items-center justify-center">
                    <Image size={16} className="text-slate-400" />
                  </div>
                )}
              </div>
              {/* Info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5">
                  <p className="text-sm font-medium text-slate-700">
                    {ev.ocr_amount ? formatINR(ev.ocr_amount) : (ev.ocr_vendor_name || "Receipt")}
                  </p>
                  <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-full ${strength.bg} ${strength.text}`}>
                    {strength.label}
                  </span>
                </div>
                <p className="text-xs text-slate-400">
                  {ev.ocr_date ? formatDate(ev.ocr_date) : timeAgo(ev.created_at)}
                  {" · "}{ev.ocr_document_type || "Document"}
                </p>
              </div>
              {/* Status */}
              <OcrStatusPill status={ev.ocr_status} />
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Upload zone ──────────────────────────────────────────────────────

function UploadZone({ onUpload, uploading }) {
  const inputRef = useRef(null);
  const [dragging, setDragging] = useState(false);

  const handleFile = useCallback((file) => {
    if (!file) return;
    const allowed = ["image/jpeg", "image/png", "image/webp", "application/pdf"];
    if (!allowed.includes(file.type)) {
      toast.error("Only JPG, PNG, WebP, or PDF files are supported.");
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      toast.error("File must be under 10 MB.");
      return;
    }
    onUpload(file);
  }, [onUpload]);

  const onDrop = useCallback((e) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    handleFile(file);
  }, [handleFile]);

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
      onClick={() => !uploading && inputRef.current?.click()}
      className={`relative flex flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed cursor-pointer transition-all py-10 px-6
        ${dragging ? "border-blue-500 bg-blue-50" : "border-slate-300 bg-slate-50 hover:border-blue-400 hover:bg-blue-50/50"}
        ${uploading ? "cursor-not-allowed opacity-70" : ""}
      `}
    >
      <input
        ref={inputRef}
        type="file"
        className="hidden"
        accept="image/jpeg,image/png,image/webp,application/pdf"
        onChange={(e) => handleFile(e.target.files[0])}
        disabled={uploading}
      />

      {uploading ? (
        <>
          <div className="w-16 h-16 rounded-full bg-blue-100 flex items-center justify-center">
            <Loader2 size={28} className="text-blue-700 animate-spin" />
          </div>
          <p className="text-sm font-semibold text-blue-700">Uploading…</p>
          <p className="text-xs text-slate-400">Please wait</p>
        </>
      ) : (
        <>
          <div className={`w-16 h-16 rounded-full flex items-center justify-center transition-colors ${dragging ? "bg-blue-200" : "bg-white border-2 border-slate-200"}`}>
            <Upload size={28} className={dragging ? "text-blue-700" : "text-slate-400"} />
          </div>
          <div className="text-center">
            <p className="text-sm font-semibold text-slate-700">
              {dragging ? "Drop it here" : "Tap to upload a receipt"}
            </p>
            <p className="text-xs text-slate-400 mt-1">JPG, PNG, WebP or PDF · Max 10 MB</p>
          </div>
          <div className="flex items-center gap-3 mt-1">
            <button
              onClick={(e) => { e.stopPropagation(); inputRef.current?.click(); }}
              className="flex items-center gap-1.5 text-xs font-semibold text-blue-700 bg-blue-100 hover:bg-blue-200 px-3 py-1.5 rounded-lg transition-colors"
            >
              <Image size={13} /> Choose File
            </button>
            <span className="text-xs text-slate-300">or</span>
            <button
              onClick={(e) => { e.stopPropagation(); inputRef.current?.click(); }}
              className="flex items-center gap-1.5 text-xs font-semibold text-slate-600 bg-slate-200 hover:bg-slate-300 px-3 py-1.5 rounded-lg transition-colors"
            >
              <Camera size={13} /> Take Photo
            </button>
          </div>
        </>
      )}
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────

export default function EvidencePage() {
  const { org } = useAuthStore();
  const qc = useQueryClient();
  const businessId = org?.id;

  const [uploading, setUploading]         = useState(false);
  const [uploadedIds, setUploadedIds]     = useState([]);

  const handleUpload = async (file) => {
    setUploading(true);
    try {
      const res = await evidenceApi.upload(file);
      const ev  = res.data.data;

      if (ev.quality_status === "rejected") {
        toast.error("Photo was rejected — too blurry or unreadable. Please try another.");
        return;
      }
      if (ev.quality_warning) {
        toast.warning(ev.quality_warning);
      } else {
        toast.success("Receipt uploaded! Scanning for details…");
      }

      setUploadedIds((prev) => [ev.evidence_id, ...prev]);
      qc.invalidateQueries({ queryKey: ["evidence-list", businessId] });
    } catch (err) {
      toast.error(getApiError(err));
    } finally {
      setUploading(false);
    }
  };

  const dismissCard = (id) => setUploadedIds((prev) => prev.filter((x) => x !== id));

  return (
    <div className="px-4 py-5 space-y-5">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-slate-800">Receipts & Evidence</h1>
        <p className="text-sm text-slate-400 mt-0.5">
          Upload bills and receipts. Our AI will scan them automatically.
        </p>
      </div>

      {/* Info bar */}
      <div className="bg-blue-50 border border-blue-200 rounded-2xl px-4 py-3 flex items-start gap-3">
        <ShieldCheck size={16} className="text-blue-600 mt-0.5 shrink-0" />
        <p className="text-xs text-blue-800 leading-relaxed">
          Strong evidence improves your compliance score. Upload receipts for every
          purchase or sale to keep your records accurate.
        </p>
      </div>

      {/* Upload zone */}
      <UploadZone onUpload={handleUpload} uploading={uploading} />

      {/* Newly uploaded results */}
      {uploadedIds.length > 0 && (
        <div className="space-y-3">
          <p className="text-xs font-bold text-slate-500 uppercase tracking-wide">
            Just Uploaded
          </p>
          {uploadedIds.map((id) => (
            <EvidenceResultCard key={id} evidenceId={id} onDismiss={() => dismissCard(id)} />
          ))}
        </div>
      )}

      {/* Recent evidence */}
      {businessId && (
        <div className="space-y-2">
          <p className="text-xs font-bold text-slate-500 uppercase tracking-wide">
            Previous Receipts
          </p>
          <RecentEvidenceList businessId={businessId} />
        </div>
      )}
    </div>
  );
}
