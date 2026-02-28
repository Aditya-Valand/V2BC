/**
 * GST Invoice Generator — /invoice
 *
 * Client-only page. Generates a print-ready GST invoice.
 * No backend required — pure client-side PDF via window.print().
 *
 * Supports:
 *  - Seller / Buyer details
 *  - Line items with HSN code, quantity, unit price, GST %
 *  - Auto-computed CGST + SGST breakdown (or IGST for inter-state)
 *  - Invoice number + date auto-fill
 *  - Print → PDF via browser print dialog
 */
"use client";

import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import {
  Plus, Trash2, Printer, ArrowLeft, FileText,
  AlertCircle,
} from "lucide-react";
import useAuthStore from "@/store/authStore";

// ── constants ──────────────────────────────────────────────────────── //
const GST_RATES = [0, 3, 5, 12, 18, 28];
const TODAY = new Date().toISOString().split("T")[0];
const INVOICE_NO = `INV-${Date.now().toString().slice(-6)}`;

const INDIAN_STATES = [
  "Andhra Pradesh","Arunachal Pradesh","Assam","Bihar","Chhattisgarh",
  "Goa","Gujarat","Haryana","Himachal Pradesh","Jharkhand","Karnataka",
  "Kerala","Madhya Pradesh","Maharashtra","Manipur","Meghalaya","Mizoram",
  "Nagaland","Odisha","Punjab","Rajasthan","Sikkim","Tamil Nadu","Telangana",
  "Tripura","Uttar Pradesh","Uttarakhand","West Bengal",
  "Delhi","Jammu & Kashmir","Ladakh","Chandigarh","Puducherry",
];

const emptyLine = () => ({
  id:          crypto.randomUUID(),
  description: "",
  hsn:         "",
  qty:         1,
  unit:        "Nos",
  unit_price:  0,
  gst_rate:    18,
});

// ── helpers ────────────────────────────────────────────────────────── //
function fmt(n) {
  return Number(n || 0).toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function lineTotal(item) {
  return (parseFloat(item.qty) || 0) * (parseFloat(item.unit_price) || 0);
}

function lineTax(item) {
  return lineTotal(item) * ((parseFloat(item.gst_rate) || 0) / 100);
}

function numToWords(num) {
  // Simple implementation for amounts up to 99 lakhs
  const ones = ["","One","Two","Three","Four","Five","Six","Seven","Eight","Nine",
    "Ten","Eleven","Twelve","Thirteen","Fourteen","Fifteen","Sixteen","Seventeen",
    "Eighteen","Nineteen"];
  const tens = ["","","Twenty","Thirty","Forty","Fifty","Sixty","Seventy","Eighty","Ninety"];

  if (num === 0) return "Zero Rupees Only";

  const rupees = Math.floor(num);
  const paise  = Math.round((num - rupees) * 100);

  function convert(n) {
    if (n < 20) return ones[n];
    if (n < 100) return tens[Math.floor(n/10)] + (n%10 ? " " + ones[n%10] : "");
    if (n < 1000) return ones[Math.floor(n/100)] + " Hundred" + (n%100 ? " " + convert(n%100) : "");
    if (n < 100000) return convert(Math.floor(n/1000)) + " Thousand" + (n%1000 ? " " + convert(n%1000) : "");
    if (n < 10000000) return convert(Math.floor(n/100000)) + " Lakh" + (n%100000 ? " " + convert(n%100000) : "");
    return convert(Math.floor(n/10000000)) + " Crore" + (n%10000000 ? " " + convert(n%10000000) : "");
  }

  let words = convert(rupees) + " Rupees";
  if (paise > 0) words += " and " + convert(paise) + " Paise";
  return words + " Only";
}

// ── Input components ───────────────────────────────────────────────── //
function Field({ label, children, className = "" }) {
  return (
    <div className={className}>
      <label className="block text-xs font-medium text-slate-500 mb-1">{label}</label>
      {children}
    </div>
  );
}

const inp = "w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white";

// ── Main Page ──────────────────────────────────────────────────────── //
export default function InvoicePage() {
  const router = useRouter();
  const { user, org } = useAuthStore();
  const printRef = useRef(null);

  // ─ Invoice meta ─
  const [invoiceNo,   setInvoiceNo]   = useState(INVOICE_NO);
  const [invoiceDate, setInvoiceDate] = useState(TODAY);
  const [dueDate,     setDueDate]     = useState("");

  // ─ Seller ─
  const [sellerName,    setSellerName]    = useState(user?.name || "");
  const [sellerGSTIN,   setSellerGSTIN]   = useState("");
  const [sellerAddr,    setSellerAddr]    = useState("");
  const [sellerState,   setSellerState]   = useState("");
  const [sellerPhone,   setSellerPhone]   = useState(user?.phone || "");

  // ─ Buyer ─
  const [buyerName,     setBuyerName]     = useState("");
  const [buyerGSTIN,    setBuyerGSTIN]    = useState("");
  const [buyerAddr,     setBuyerAddr]     = useState("");
  const [buyerState,    setBuyerState]    = useState("");

  // ─ Line items ─
  const [items, setItems] = useState([emptyLine()]);

  // ─ Notes ─
  const [notes, setNotes] = useState("Payment due within 30 days. Thank you for your business.");

  // ─ Inter-state toggle ─
  const isInterState = sellerState && buyerState && sellerState !== buyerState;

  // ── Computed totals ──────────────────────────────────────────────── //
  const subtotal   = items.reduce((s, it) => s + lineTotal(it), 0);
  const totalGST   = items.reduce((s, it) => s + lineTax(it), 0);
  const grandTotal = subtotal + totalGST;

  // ── Line item handlers ───────────────────────────────────────────── //
  const updateItem = (id, field, value) =>
    setItems((prev) => prev.map((it) => it.id === id ? { ...it, [field]: value } : it));

  const addItem = () => setItems((prev) => [...prev, emptyLine()]);

  const removeItem = (id) => {
    if (items.length === 1) return;
    setItems((prev) => prev.filter((it) => it.id !== id));
  };

  // ── Print ────────────────────────────────────────────────────────── //
  const handlePrint = () => {
    if (!sellerName) { alert("Please enter your business name first."); return; }
    window.print();
  };

  // ── GST breakdown per rate ───────────────────────────────────────── //
  const taxByRate = items.reduce((acc, it) => {
    const rate = parseFloat(it.gst_rate) || 0;
    const base = lineTotal(it);
    const tax  = base * rate / 100;
    if (!acc[rate]) acc[rate] = { base: 0, tax: 0 };
    acc[rate].base += base;
    acc[rate].tax  += tax;
    return acc;
  }, {});

  // ── Render ───────────────────────────────────────────────────────── //
  return (
    <>
      {/* ── Print-only styles ── */}
      <style>{`
        @media print {
          body > *:not(#invoice-print-root) { display: none !important; }
          #invoice-print-root { display: block !important; }
          .no-print { display: none !important; }
          .print-only { display: block !important; }
          @page { margin: 10mm; size: A4; }
        }
        .print-only { display: none; }
      `}</style>

      {/* ── Screen layout ── */}
      <div className="min-h-screen bg-slate-50 pb-24 no-print">
        {/* Topbar */}
        <div className="sticky top-0 z-20 bg-white border-b border-slate-200 px-4 py-3 flex items-center justify-between">
          <button
            onClick={() => router.back()}
            className="flex items-center gap-1.5 text-slate-600 hover:text-slate-900"
          >
            <ArrowLeft size={18} />
            <span className="text-sm font-medium">Back</span>
          </button>
          <h1 className="text-sm font-bold text-slate-800">GST Invoice</h1>
          <button
            onClick={handlePrint}
            className="flex items-center gap-1.5 bg-blue-700 text-white text-sm font-semibold px-3 py-1.5 rounded-lg hover:bg-blue-800"
          >
            <Printer size={15} />
            Print / PDF
          </button>
        </div>

        <div className="max-w-2xl mx-auto px-4 pt-4 space-y-4">

          {/* Info banner */}
          <div className="bg-blue-50 border border-blue-200 rounded-xl p-3 flex gap-2 text-xs text-blue-700">
            <AlertCircle size={14} className="shrink-0 mt-0.5" />
            <span>Fill in details, then tap <strong>Print / PDF</strong> to download as PDF via your browser&apos;s print dialog.</span>
          </div>

          {/* Invoice meta */}
          <section className="bg-white rounded-2xl p-4 shadow-sm border border-slate-100">
            <h2 className="text-sm font-bold text-slate-700 mb-3">Invoice Details</h2>
            <div className="grid grid-cols-3 gap-3">
              <Field label="Invoice No." className="col-span-1">
                <input className={inp} value={invoiceNo} onChange={(e) => setInvoiceNo(e.target.value)} />
              </Field>
              <Field label="Invoice Date" className="col-span-1">
                <input className={inp} type="date" value={invoiceDate} onChange={(e) => setInvoiceDate(e.target.value)} />
              </Field>
              <Field label="Due Date" className="col-span-1">
                <input className={inp} type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} placeholder="Optional" />
              </Field>
            </div>
          </section>

          {/* Seller */}
          <section className="bg-white rounded-2xl p-4 shadow-sm border border-slate-100">
            <h2 className="text-sm font-bold text-slate-700 mb-3">From (Seller / Your Business)</h2>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Business / Name *" className="col-span-2">
                <input className={inp} value={sellerName} onChange={(e) => setSellerName(e.target.value)} placeholder="Your business name" />
              </Field>
              <Field label="GSTIN" className="col-span-1">
                <input className={`${inp} uppercase`} value={sellerGSTIN} onChange={(e) => setSellerGSTIN(e.target.value.toUpperCase())} placeholder="22AAAAA0000A1Z5" maxLength={15} />
              </Field>
              <Field label="Phone" className="col-span-1">
                <input className={inp} value={sellerPhone} onChange={(e) => setSellerPhone(e.target.value)} placeholder="10-digit mobile" />
              </Field>
              <Field label="State" className="col-span-1">
                <select className={inp} value={sellerState} onChange={(e) => setSellerState(e.target.value)}>
                  <option value="">Select state</option>
                  {INDIAN_STATES.map((s) => <option key={s} value={s}>{s}</option>)}
                </select>
              </Field>
              <Field label="Address" className="col-span-2">
                <textarea className={`${inp} resize-none`} rows={2} value={sellerAddr} onChange={(e) => setSellerAddr(e.target.value)} placeholder="Street, City, PIN" />
              </Field>
            </div>
          </section>

          {/* Buyer */}
          <section className="bg-white rounded-2xl p-4 shadow-sm border border-slate-100">
            <h2 className="text-sm font-bold text-slate-700 mb-3">To (Buyer / Customer)</h2>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Customer Name *" className="col-span-2">
                <input className={inp} value={buyerName} onChange={(e) => setBuyerName(e.target.value)} placeholder="Customer / Company name" />
              </Field>
              <Field label="GSTIN" className="col-span-1">
                <input className={`${inp} uppercase`} value={buyerGSTIN} onChange={(e) => setBuyerGSTIN(e.target.value.toUpperCase())} placeholder="Optional" maxLength={15} />
              </Field>
              <Field label="State" className="col-span-1">
                <select className={inp} value={buyerState} onChange={(e) => setBuyerState(e.target.value)}>
                  <option value="">Select state</option>
                  {INDIAN_STATES.map((s) => <option key={s} value={s}>{s}</option>)}
                </select>
              </Field>
              <Field label="Address" className="col-span-2">
                <textarea className={`${inp} resize-none`} rows={2} value={buyerAddr} onChange={(e) => setBuyerAddr(e.target.value)} placeholder="Street, City, PIN" />
              </Field>
            </div>
            {isInterState && (
              <p className="mt-2 text-xs text-amber-600 bg-amber-50 rounded-lg px-3 py-1.5">
                Inter-state supply detected — IGST will apply instead of CGST + SGST.
              </p>
            )}
          </section>

          {/* Line items */}
          <section className="bg-white rounded-2xl p-4 shadow-sm border border-slate-100">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-bold text-slate-700">Items / Services</h2>
              <button onClick={addItem} className="flex items-center gap-1 text-blue-600 text-xs font-semibold hover:text-blue-800">
                <Plus size={14} /> Add Row
              </button>
            </div>

            <div className="overflow-x-auto -mx-1">
              <table className="w-full text-xs min-w-[560px]">
                <thead>
                  <tr className="bg-slate-50 text-slate-500 font-semibold">
                    <th className="p-2 text-left">Description</th>
                    <th className="p-2 text-left w-20">HSN</th>
                    <th className="p-2 text-right w-14">Qty</th>
                    <th className="p-2 text-left w-16">Unit</th>
                    <th className="p-2 text-right w-24">Rate (₹)</th>
                    <th className="p-2 text-right w-16">GST %</th>
                    <th className="p-2 text-right w-24">Amount (₹)</th>
                    <th className="p-2 w-8"></th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => (
                    <tr key={item.id} className="border-t border-slate-100">
                      <td className="p-1.5">
                        <input
                          className="w-full border border-slate-200 rounded px-2 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-blue-400"
                          value={item.description}
                          onChange={(e) => updateItem(item.id, "description", e.target.value)}
                          placeholder="Item / service name"
                        />
                      </td>
                      <td className="p-1.5">
                        <input
                          className="w-full border border-slate-200 rounded px-2 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-blue-400"
                          value={item.hsn}
                          onChange={(e) => updateItem(item.id, "hsn", e.target.value)}
                          placeholder="HSN"
                        />
                      </td>
                      <td className="p-1.5">
                        <input
                          type="number" min="0.01" step="0.01"
                          className="w-full border border-slate-200 rounded px-2 py-1.5 text-xs text-right focus:outline-none focus:ring-1 focus:ring-blue-400"
                          value={item.qty}
                          onChange={(e) => updateItem(item.id, "qty", e.target.value)}
                        />
                      </td>
                      <td className="p-1.5">
                        <input
                          className="w-full border border-slate-200 rounded px-2 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-blue-400"
                          value={item.unit}
                          onChange={(e) => updateItem(item.id, "unit", e.target.value)}
                          placeholder="Nos"
                        />
                      </td>
                      <td className="p-1.5">
                        <input
                          type="number" min="0" step="0.01"
                          className="w-full border border-slate-200 rounded px-2 py-1.5 text-xs text-right focus:outline-none focus:ring-1 focus:ring-blue-400"
                          value={item.unit_price}
                          onChange={(e) => updateItem(item.id, "unit_price", e.target.value)}
                        />
                      </td>
                      <td className="p-1.5">
                        <select
                          className="w-full border border-slate-200 rounded px-2 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-blue-400"
                          value={item.gst_rate}
                          onChange={(e) => updateItem(item.id, "gst_rate", e.target.value)}
                        >
                          {GST_RATES.map((r) => <option key={r} value={r}>{r}%</option>)}
                        </select>
                      </td>
                      <td className="p-1.5 text-right font-semibold text-slate-700">
                        {fmt(lineTotal(item) + lineTax(item))}
                      </td>
                      <td className="p-1.5">
                        <button
                          onClick={() => removeItem(item.id)}
                          className="text-red-400 hover:text-red-600 disabled:opacity-30"
                          disabled={items.length === 1}
                        >
                          <Trash2 size={13} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Totals */}
            <div className="mt-4 border-t border-slate-200 pt-3 space-y-1.5 text-xs">
              <div className="flex justify-between text-slate-600">
                <span>Subtotal (before GST)</span>
                <span className="font-medium">₹{fmt(subtotal)}</span>
              </div>
              {Object.entries(taxByRate).filter(([, v]) => v.tax > 0).map(([rate, v]) => (
                isInterState ? (
                  <div key={rate} className="flex justify-between text-slate-600">
                    <span>IGST @ {rate}% on ₹{fmt(v.base)}</span>
                    <span>₹{fmt(v.tax)}</span>
                  </div>
                ) : (
                  <div key={rate}>
                    <div className="flex justify-between text-slate-600">
                      <span>CGST @ {rate/2}% on ₹{fmt(v.base)}</span>
                      <span>₹{fmt(v.tax/2)}</span>
                    </div>
                    <div className="flex justify-between text-slate-600">
                      <span>SGST @ {rate/2}% on ₹{fmt(v.base)}</span>
                      <span>₹{fmt(v.tax/2)}</span>
                    </div>
                  </div>
                )
              ))}
              <div className="flex justify-between font-bold text-slate-900 text-sm border-t border-slate-200 pt-2">
                <span>Grand Total</span>
                <span>₹{fmt(grandTotal)}</span>
              </div>
              <p className="text-slate-400 italic">{numToWords(grandTotal)}</p>
            </div>
          </section>

          {/* Notes */}
          <section className="bg-white rounded-2xl p-4 shadow-sm border border-slate-100">
            <h2 className="text-sm font-bold text-slate-700 mb-2">Notes / Terms</h2>
            <textarea
              className={`${inp} resize-none`}
              rows={3}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Payment terms, bank details, thank-you note..."
            />
          </section>

        </div>
      </div>

      {/* ──────────────────────────────────────────── */}
      {/* PRINT TEMPLATE — only visible when printing  */}
      {/* ──────────────────────────────────────────── */}
      <div id="invoice-print-root" ref={printRef} style={{ display: "none", fontFamily: "Arial, sans-serif", fontSize: "11px", color: "#1a1a1a", padding: "8mm", maxWidth: "210mm" }}>

        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "2px solid #1d4ed8", paddingBottom: "8px", marginBottom: "12px" }}>
          <div>
            <div style={{ fontSize: "18px", fontWeight: "bold", color: "#1d4ed8" }}>TAX INVOICE</div>
            <div style={{ fontSize: "10px", color: "#6b7280", marginTop: "2px" }}>BharatCompliance · India</div>
          </div>
          <div style={{ textAlign: "right" }}>
            <div><strong>Invoice No:</strong> {invoiceNo}</div>
            <div><strong>Date:</strong> {invoiceDate}</div>
            {dueDate && <div><strong>Due:</strong> {dueDate}</div>}
          </div>
        </div>

        {/* Seller / Buyer */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px", marginBottom: "12px" }}>
          <div style={{ border: "1px solid #e5e7eb", borderRadius: "6px", padding: "8px" }}>
            <div style={{ fontSize: "9px", fontWeight: "bold", color: "#6b7280", marginBottom: "4px" }}>FROM (SELLER)</div>
            <div style={{ fontWeight: "bold", fontSize: "13px" }}>{sellerName || "—"}</div>
            {sellerGSTIN && <div>GSTIN: {sellerGSTIN}</div>}
            {sellerState && <div>State: {sellerState}</div>}
            {sellerAddr  && <div style={{ color: "#6b7280", marginTop: "4px" }}>{sellerAddr}</div>}
            {sellerPhone && <div>Ph: {sellerPhone}</div>}
          </div>
          <div style={{ border: "1px solid #e5e7eb", borderRadius: "6px", padding: "8px" }}>
            <div style={{ fontSize: "9px", fontWeight: "bold", color: "#6b7280", marginBottom: "4px" }}>TO (BUYER)</div>
            <div style={{ fontWeight: "bold", fontSize: "13px" }}>{buyerName || "—"}</div>
            {buyerGSTIN && <div>GSTIN: {buyerGSTIN}</div>}
            {buyerState && <div>State: {buyerState}</div>}
            {buyerAddr  && <div style={{ color: "#6b7280", marginTop: "4px" }}>{buyerAddr}</div>}
          </div>
        </div>

        {/* Items table */}
        <table style={{ width: "100%", borderCollapse: "collapse", marginBottom: "12px" }}>
          <thead>
            <tr style={{ background: "#1d4ed8", color: "white" }}>
              {["#","Description","HSN","Qty","Unit","Rate (₹)","GST%","Taxable (₹)",
                isInterState ? "IGST (₹)" : "CGST (₹)", !isInterState && "SGST (₹)", "Total (₹)"]
                .filter(Boolean).map((h) => (
                <th key={h} style={{ padding: "5px 8px", textAlign: h === "#" ? "center" : "right", textAlign: ["#","Description","HSN","Unit"].includes(h) ? "left" : "right", fontSize: "9px" }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {items.map((it, idx) => {
              const base = lineTotal(it);
              const tax  = lineTax(it);
              return (
                <tr key={it.id} style={{ background: idx % 2 === 0 ? "#f9fafb" : "white", borderBottom: "1px solid #e5e7eb" }}>
                  <td style={{ padding: "5px 8px" }}>{idx + 1}</td>
                  <td style={{ padding: "5px 8px" }}>{it.description}</td>
                  <td style={{ padding: "5px 8px" }}>{it.hsn}</td>
                  <td style={{ padding: "5px 8px", textAlign: "right" }}>{it.qty}</td>
                  <td style={{ padding: "5px 8px" }}>{it.unit}</td>
                  <td style={{ padding: "5px 8px", textAlign: "right" }}>{fmt(it.unit_price)}</td>
                  <td style={{ padding: "5px 8px", textAlign: "right" }}>{it.gst_rate}%</td>
                  <td style={{ padding: "5px 8px", textAlign: "right" }}>{fmt(base)}</td>
                  {isInterState
                    ? <td style={{ padding: "5px 8px", textAlign: "right" }}>{fmt(tax)}</td>
                    : <>
                        <td style={{ padding: "5px 8px", textAlign: "right" }}>{fmt(tax/2)}</td>
                        <td style={{ padding: "5px 8px", textAlign: "right" }}>{fmt(tax/2)}</td>
                      </>
                  }
                  <td style={{ padding: "5px 8px", textAlign: "right", fontWeight: "bold" }}>{fmt(base + tax)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>

        {/* Totals */}
        <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: "12px" }}>
          <table style={{ minWidth: "240px", fontSize: "11px" }}>
            <tbody>
              <tr><td style={{ padding: "3px 8px", color: "#6b7280" }}>Subtotal</td><td style={{ padding: "3px 8px", textAlign: "right" }}>₹{fmt(subtotal)}</td></tr>
              {Object.entries(taxByRate).filter(([,v]) => v.tax > 0).map(([rate, v]) =>
                isInterState
                  ? <tr key={rate}><td style={{ padding: "3px 8px", color: "#6b7280" }}>IGST @ {rate}%</td><td style={{ padding: "3px 8px", textAlign: "right" }}>₹{fmt(v.tax)}</td></tr>
                  : <>
                      <tr key={`c${rate}`}><td style={{ padding: "3px 8px", color: "#6b7280" }}>CGST @ {rate/2}%</td><td style={{ padding: "3px 8px", textAlign: "right" }}>₹{fmt(v.tax/2)}</td></tr>
                      <tr key={`s${rate}`}><td style={{ padding: "3px 8px", color: "#6b7280" }}>SGST @ {rate/2}%</td><td style={{ padding: "3px 8px", textAlign: "right" }}>₹{fmt(v.tax/2)}</td></tr>
                    </>
              )}
              <tr style={{ background: "#1d4ed8", color: "white" }}>
                <td style={{ padding: "6px 8px", fontWeight: "bold" }}>Grand Total</td>
                <td style={{ padding: "6px 8px", textAlign: "right", fontWeight: "bold" }}>₹{fmt(grandTotal)}</td>
              </tr>
            </tbody>
          </table>
        </div>

        {/* Amount in words */}
        <div style={{ background: "#f3f4f6", borderRadius: "4px", padding: "6px 10px", fontSize: "10px", marginBottom: "12px" }}>
          <strong>Amount in Words:</strong> {numToWords(grandTotal)}
        </div>

        {/* Notes */}
        {notes && (
          <div style={{ fontSize: "10px", color: "#6b7280", borderTop: "1px solid #e5e7eb", paddingTop: "8px", marginBottom: "12px" }}>
            <strong>Notes / Terms:</strong> {notes}
          </div>
        )}

        {/* Footer */}
        <div style={{ borderTop: "1px solid #e5e7eb", paddingTop: "8px", display: "flex", justifyContent: "space-between", fontSize: "9px", color: "#9ca3af" }}>
          <span>Generated via BharatCompliance · bharatcomplianceb.onrender.com</span>
          <div style={{ textAlign: "right" }}>
            <div style={{ height: "32px", borderBottom: "1px solid #374151", width: "120px", marginLeft: "auto" }}></div>
            <div style={{ marginTop: "4px" }}>Authorised Signatory</div>
          </div>
        </div>
      </div>
    </>
  );
}
