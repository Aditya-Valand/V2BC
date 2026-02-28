/**
 * Bank Statement Import — /import-statement
 *
 * Client-only page. Upload a CSV bank statement to auto-create transactions.
 *
 * Supported column formats:
 *  Generic:       date, description, amount, type
 *  Debit/Credit:  date, description, debit, credit
 *  SBI format:    Date, Description, Amount (Debit), Amount (Credit)
 *  HDFC format:   Date, Narration, Withdrawal Amt., Deposit Amt.
 *  ICICI format:  Date, Particulars, Withdrawals, Deposits
 */
"use client";

import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowLeft, Upload, FileText, CheckCircle2, XCircle,
  AlertTriangle, ChevronDown, ChevronUp, Info,
} from "lucide-react";
import { toast } from "sonner";
import apiClient from "@/lib/api/client";

// ── Template CSV for download ────────────────────────────────────────── //
const TEMPLATE_CSV = `date,description,credit,debit
2024-01-05,Payment received from customer,5000,
2024-01-08,Raw material purchase,,2200
2024-01-12,Freelance project income,8500,
2024-01-15,Electricity bill,,950
`;

function downloadTemplate() {
  const blob = new Blob([TEMPLATE_CSV], { type: "text/csv" });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement("a");
  a.href     = url;
  a.download = "bank_statement_template.csv";
  a.click();
  URL.revokeObjectURL(url);
}

// ── Sub-components ───────────────────────────────────────────────────── //
function ResultRow({ item, type }) {
  const isCreated = type === "created";
  return (
    <div className={`flex items-start gap-2 py-2 border-b border-slate-100 last:border-0 ${isCreated ? "" : "opacity-70"}`}>
      {isCreated
        ? <CheckCircle2 size={14} className="text-green-500 shrink-0 mt-0.5" />
        : <XCircle     size={14} className="text-red-400 shrink-0 mt-0.5" />
      }
      <div className="flex-1 min-w-0 text-xs">
        {isCreated ? (
          <div>
            <span className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-bold mr-1.5 ${
              item.type === "sale" ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"
            }`}>
              {item.type === "sale" ? "SALE" : "EXPENSE"}
            </span>
            <span className="font-semibold text-slate-700">₹{Number(item.amount).toLocaleString("en-IN")}</span>
            <span className="text-slate-400 ml-1.5">{item.date}</span>
            {item.desc && <p className="text-slate-500 truncate mt-0.5">{item.desc}</p>}
            {item.warning && (
              <p className="text-amber-600 mt-0.5 flex items-center gap-1">
                <AlertTriangle size={10} /> {item.warning}
              </p>
            )}
          </div>
        ) : (
          <div>
            <span className="text-slate-500">Row {item.row}</span>
            {item.name && <span className="ml-1.5 font-medium text-slate-700">{item.name}</span>}
            <span className="ml-1.5 text-red-500">{item.reason}</span>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Page ─────────────────────────────────────────────────────────────── //
export default function ImportStatementPage() {
  const router = useRouter();
  const fileRef = useRef(null);

  const [file,     setFile]     = useState(null);
  const [loading,  setLoading]  = useState(false);
  const [result,   setResult]   = useState(null);
  const [showSkipped, setShowSkipped] = useState(false);

  const handleFileChange = (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    if (!f.name.toLowerCase().endsWith(".csv")) {
      toast.error("Only CSV files are supported.");
      return;
    }
    if (f.size > 2_000_000) {
      toast.error("File too large. Maximum 2 MB.");
      return;
    }
    setFile(f);
    setResult(null);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    const f = e.dataTransfer.files?.[0];
    if (f) {
      if (!f.name.toLowerCase().endsWith(".csv")) { toast.error("Only CSV files are supported."); return; }
      setFile(f);
      setResult(null);
    }
  };

  const handleUpload = async () => {
    if (!file) { toast.error("Please select a CSV file first."); return; }
    setLoading(true);
    setResult(null);
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await apiClient.post("/my/import-bank-statement", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      const data = res.data.data;
      setResult(data);
      if (data.created_count > 0) {
        toast.success(`${data.created_count} transaction${data.created_count > 1 ? "s" : ""} imported!`);
      } else {
        toast.warning("No transactions could be imported. Check the skipped rows.");
      }
    } catch (err) {
      const msg = err.response?.data?.error || "Upload failed. Try again.";
      if (typeof msg === "string") toast.error(msg);
      else toast.error("Invalid CSV format. Please check the template.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 pb-24">

      {/* Topbar */}
      <div className="sticky top-0 z-20 bg-white border-b border-slate-200 px-4 py-3 flex items-center justify-between">
        <button
          onClick={() => router.back()}
          className="flex items-center gap-1.5 text-slate-600 hover:text-slate-900"
        >
          <ArrowLeft size={18} />
          <span className="text-sm font-medium">Back</span>
        </button>
        <h1 className="text-sm font-bold text-slate-800">Import Bank Statement</h1>
        <div className="w-16" />
      </div>

      <div className="max-w-lg mx-auto px-4 pt-4 space-y-4">

        {/* Info card */}
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-3 text-xs text-blue-700 space-y-1">
          <div className="flex items-center gap-1.5 font-semibold">
            <Info size={13} /> Supported CSV formats
          </div>
          <ul className="list-disc list-inside space-y-0.5 text-blue-600">
            <li>Generic: <code>date, description, credit, debit</code></li>
            <li>SBI: <code>Date, Description, Amount (Debit), Amount (Credit)</code></li>
            <li>HDFC: <code>Date, Narration, Withdrawal Amt., Deposit Amt.</code></li>
            <li>ICICI: <code>Date, Particulars, Withdrawals, Deposits</code></li>
          </ul>
          <button
            onClick={downloadTemplate}
            className="mt-1 flex items-center gap-1 text-blue-700 font-semibold underline underline-offset-2"
          >
            <FileText size={12} /> Download template CSV
          </button>
        </div>

        {/* Drop zone */}
        <div
          onDrop={handleDrop}
          onDragOver={(e) => e.preventDefault()}
          onClick={() => fileRef.current?.click()}
          className={`border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-colors
            ${file
              ? "border-green-400 bg-green-50"
              : "border-slate-300 bg-white hover:border-blue-400 hover:bg-blue-50"
            }`}
        >
          <input
            ref={fileRef}
            type="file"
            accept=".csv"
            className="hidden"
            onChange={handleFileChange}
          />
          {file ? (
            <div className="space-y-1">
              <CheckCircle2 size={32} className="text-green-500 mx-auto" />
              <p className="text-sm font-semibold text-green-700">{file.name}</p>
              <p className="text-xs text-green-600">{(file.size / 1024).toFixed(1)} KB · Click to change</p>
            </div>
          ) : (
            <div className="space-y-2">
              <Upload size={32} className="text-slate-400 mx-auto" />
              <p className="text-sm font-semibold text-slate-700">Drop your CSV here</p>
              <p className="text-xs text-slate-400">or click to browse · Max 2 MB · 500 rows</p>
            </div>
          )}
        </div>

        {/* Upload button */}
        <button
          onClick={handleUpload}
          disabled={!file || loading}
          className="w-full bg-blue-700 text-white text-sm font-semibold py-3 rounded-xl hover:bg-blue-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
        >
          {loading ? (
            <>
              <div className="w-4 h-4 rounded-full border-2 border-white border-t-transparent animate-spin" />
              Processing…
            </>
          ) : (
            <>
              <Upload size={16} />
              Import Transactions
            </>
          )}
        </button>

        {/* Results */}
        {result && (
          <div className="space-y-3">

            {/* Summary row */}
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-green-50 border border-green-200 rounded-xl p-4 text-center">
                <p className="text-2xl font-bold text-green-700">{result.created_count}</p>
                <p className="text-xs text-green-600 mt-1">Transactions Imported</p>
              </div>
              <div className={`border rounded-xl p-4 text-center ${result.skipped_count > 0 ? "bg-amber-50 border-amber-200" : "bg-slate-50 border-slate-200"}`}>
                <p className={`text-2xl font-bold ${result.skipped_count > 0 ? "text-amber-700" : "text-slate-500"}`}>{result.skipped_count}</p>
                <p className={`text-xs mt-1 ${result.skipped_count > 0 ? "text-amber-600" : "text-slate-400"}`}>Rows Skipped</p>
              </div>
            </div>

            {/* Created list */}
            {result.created.length > 0 && (
              <div className="bg-white rounded-2xl border border-slate-100 shadow-sm">
                <div className="px-4 py-3 border-b border-slate-100">
                  <h3 className="text-sm font-bold text-slate-700">Imported Transactions</h3>
                </div>
                <div className="px-4 py-1 max-h-64 overflow-y-auto">
                  {result.created.map((item) => (
                    <ResultRow key={`c-${item.id}`} item={item} type="created" />
                  ))}
                </div>
              </div>
            )}

            {/* Skipped list (collapsible) */}
            {result.skipped.length > 0 && (
              <div className="bg-white rounded-2xl border border-slate-100 shadow-sm">
                <button
                  className="w-full px-4 py-3 flex items-center justify-between"
                  onClick={() => setShowSkipped((p) => !p)}
                >
                  <h3 className="text-sm font-bold text-slate-700 flex items-center gap-2">
                    <AlertTriangle size={14} className="text-amber-500" />
                    {result.skipped_count} Skipped Row{result.skipped_count !== 1 ? "s" : ""}
                  </h3>
                  {showSkipped ? <ChevronUp size={14} className="text-slate-400" /> : <ChevronDown size={14} className="text-slate-400" />}
                </button>
                {showSkipped && (
                  <div className="px-4 pb-2 max-h-48 overflow-y-auto border-t border-slate-100">
                    {result.skipped.map((item, i) => (
                      <ResultRow key={i} item={item} type="skipped" />
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Done action */}
            {result.created_count > 0 && (
              <button
                onClick={() => router.push("/transactions")}
                className="w-full text-center text-blue-600 text-sm font-semibold py-3 bg-white rounded-xl border border-blue-200 hover:bg-blue-50 transition-colors"
              >
                View All Transactions →
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
