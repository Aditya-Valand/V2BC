"use client";

import { useState, useRef, useEffect, useCallback, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { format, subDays } from "date-fns";
import {
  TrendingUp, TrendingDown, Camera, ImageIcon, CheckCircle2,
  ArrowLeft, Loader2, X, Calendar, Sparkles, Mic,
  ShieldCheck, AlertTriangle, ChevronRight,
} from "lucide-react";
import { toast } from "sonner";
import { transactionsApi } from "@/lib/api/transactions";
import { validationApi } from "@/lib/api/validation";
import { evidenceApi } from "@/lib/api/evidence";
import { getApiError } from "@/lib/api/client";
import { formatINR } from "@/lib/utils";
import useAuthStore from "@/store/authStore";

// ── Constants ──────────────────────────────────────────────────────────

const SALE_CATS = [
  { value: "food_sales",     label: "Food / Tea" },
  { value: "product_sales",  label: "Products" },
  { value: "service_income", label: "Service" },
  { value: "consulting",     label: "Consulting" },
  { value: "rent_received",  label: "Rent" },
  { value: "other_income",   label: "Other" },
];

const EXPENSE_CATS = [
  { value: "food_supplies",  label: "Raw Material" },
  { value: "rent",           label: "Rent" },
  { value: "utilities",      label: "Electricity" },
  { value: "salaries",       label: "Labour" },
  { value: "transport",      label: "Transport" },
  { value: "marketing",      label: "Marketing" },
  { value: "maintenance",    label: "Repair" },
  { value: "other_expense",  label: "Other" },
];

const STEPS = {
  GREETING:  "greeting",
  AMOUNT:    "amount",
  CATEGORY:  "category",
  DATE:      "date",
  PHOTO:     "photo",
  NOTES:     "notes",
  CONFIRM:   "confirm",
  SUBMITTING:"submitting",
  OCR_CONFLICT: "ocr_conflict",
  WARN_CONFIRM: "warn_confirm",
  SUCCESS:   "success",
};

let _msgId = 0;
function mkMsg(from, text, extra = {}) {
  return { id: ++_msgId, from, text, ...extra };
}

// ── Typing indicator ───────────────────────────────────────────────────

function TypingDots() {
  return (
    <div className="flex items-center gap-1 px-4 py-3">
      <div className="w-8 h-8 rounded-full bg-blue-700 flex items-center justify-center shrink-0">
        <Sparkles size={14} className="text-white" />
      </div>
      <div className="bg-slate-100 rounded-2xl rounded-tl-sm px-4 py-3 flex items-center gap-1.5">
        <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
        <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
        <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
      </div>
    </div>
  );
}

// ── Single chat message bubble ─────────────────────────────────────────

function ChatMessage({ msg }) {
  const isBot = msg.from === "bot";

  if (msg.type === "summary_card") {
    return (
      <div className="flex items-start gap-2 px-4 py-2 msg-in">
        <div className="w-8 h-8 rounded-full bg-blue-700 flex items-center justify-center shrink-0">
          <Sparkles size={14} className="text-white" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="bg-white border border-slate-200 rounded-2xl rounded-tl-sm overflow-hidden shadow-sm">
            <div className={`px-4 py-2 text-xs font-bold text-white ${msg.meta.type === "sale" ? "bg-green-600" : "bg-red-500"}`}>
              {msg.meta.type === "sale" ? "Sale Entry" : "Expense Entry"}
            </div>
            <div className="p-4 space-y-2">
              <div className="flex justify-between items-center">
                <span className="text-xs text-slate-400">Amount</span>
                <span className="text-lg font-bold text-slate-800">{formatINR(parseFloat(msg.meta.amount))}</span>
              </div>
              {msg.meta.category && (
                <div className="flex justify-between items-center">
                  <span className="text-xs text-slate-400">Category</span>
                  <span className="text-sm font-medium text-slate-700">{msg.meta.categoryLabel}</span>
                </div>
              )}
              <div className="flex justify-between items-center">
                <span className="text-xs text-slate-400">Date</span>
                <span className="text-sm font-medium text-slate-700">{msg.meta.dateLabel}</span>
              </div>
              {msg.meta.hasPhoto && (
                <div className="flex justify-between items-center">
                  <span className="text-xs text-slate-400">Evidence</span>
                  <span className="text-xs font-semibold text-green-700 flex items-center gap-1">
                    <ShieldCheck size={12} /> Photo attached
                  </span>
                </div>
              )}
              {msg.meta.notes && (
                <div className="flex justify-between items-center">
                  <span className="text-xs text-slate-400">Note</span>
                  <span className="text-xs text-slate-600">{msg.meta.notes}</span>
                </div>
              )}
            </div>
          </div>
          <p className="text-xs text-slate-400 mt-1 ml-1">Ready to save?</p>
        </div>
      </div>
    );
  }

  if (msg.type === "photo_preview") {
    return (
      <div className="flex justify-end px-4 py-1 msg-in">
        <div className="max-w-[60%]">
          <img
            src={msg.src}
            alt="Receipt"
            className="w-full rounded-2xl rounded-br-sm shadow-md"
          />
          {msg.ocrStatus && (
            <div className={`mt-1 text-right text-xs font-medium ${
              msg.ocrStatus === "success" ? "text-green-600" :
              msg.ocrStatus === "failed"  ? "text-red-500"   : "text-blue-500"
            }`}>
              {msg.ocrStatus === "success"    ? "✓ Scanned" :
               msg.ocrStatus === "failed"     ? "Scan failed" :
               "Scanning…"}
            </div>
          )}
        </div>
      </div>
    );
  }

  if (isBot) {
    return (
      <div className="flex items-start gap-2 px-4 py-1 msg-in">
        <div className="w-8 h-8 rounded-full bg-blue-700 flex items-center justify-center shrink-0 mt-0.5">
          <Sparkles size={14} className="text-white" />
        </div>
        <div className="bg-slate-100 rounded-2xl rounded-tl-sm px-4 py-3 max-w-[80%]">
          <p className="text-sm text-slate-700 leading-relaxed">{msg.text}</p>
        </div>
      </div>
    );
  }

  // User bubble
  return (
    <div className="flex justify-end px-4 py-1 msg-in">
      <div className="bg-blue-700 text-white rounded-2xl rounded-br-sm px-4 py-2.5 max-w-[75%]">
        <p className="text-sm leading-relaxed">{msg.text}</p>
      </div>
    </div>
  );
}

// ── Amount input keyboard ──────────────────────────────────────────────

function AmountInput({ value, onChange, onConfirm, type }) {
  const isIncome = type === "sale";
  const display  = value ? `₹ ${parseFloat(value).toLocaleString("en-IN")}` : "₹ 0";

  const keys = [
    "1","2","3","4","5","6","7","8","9",".",  "0","⌫"
  ];

  const handleKey = (key) => {
    if (key === "⌫") {
      onChange(value.slice(0, -1));
    } else if (key === "." && value.includes(".")) {
      // ignore
    } else if (value.length >= 10) {
      // cap at 10 digits
    } else {
      onChange(value + key);
    }
  };

  const numVal = parseFloat(value);
  const valid  = !isNaN(numVal) && numVal > 0;

  return (
    <div className="px-4 pb-4 space-y-4">
      {/* Amount display */}
      <div className={`text-center py-4 rounded-2xl ${isIncome ? "bg-green-50" : "bg-red-50"}`}>
        <p className={`text-4xl font-bold tracking-tight ${
          value ? (isIncome ? "text-green-700" : "text-red-600") : "text-slate-300"
        }`}>
          {display}
        </p>
        {value && (
          <p className="text-xs text-slate-400 mt-1">
            {parseFloat(value).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </p>
        )}
      </div>

      {/* Numpad */}
      <div className="grid grid-cols-3 gap-2">
        {keys.map((k) => (
          <button
            key={k}
            onClick={() => handleKey(k)}
            className={`py-3.5 rounded-xl text-lg font-semibold transition-all active:scale-95 ${
              k === "⌫"
                ? "bg-slate-200 text-slate-700 hover:bg-slate-300"
                : "bg-white border border-slate-200 text-slate-800 hover:bg-slate-50 hover:border-slate-300"
            }`}
          >
            {k}
          </button>
        ))}
      </div>

      {/* Confirm button */}
      <button
        onClick={() => valid && onConfirm(value)}
        disabled={!valid}
        className={`w-full py-4 rounded-2xl font-bold text-white text-base transition-all ${
          valid
            ? isIncome
              ? "bg-green-600 hover:bg-green-700 active:scale-[0.98]"
              : "bg-red-500 hover:bg-red-600 active:scale-[0.98]"
            : "bg-slate-300 cursor-not-allowed"
        }`}
      >
        Confirm {valid ? formatINR(numVal) : "Amount"}
      </button>
    </div>
  );
}

// ── Category picker ────────────────────────────────────────────────────

function CategoryPicker({ type, onSelect }) {
  const cats = type === "sale" ? SALE_CATS : EXPENSE_CATS;
  return (
    <div className="px-4 pb-4">
      <div className="grid grid-cols-3 gap-2">
        {cats.map((c) => (
          <button
            key={c.value}
            onClick={() => onSelect(c)}
            className="py-3 px-2 bg-white border border-slate-200 rounded-xl text-xs font-semibold text-slate-700 hover:border-blue-400 hover:bg-blue-50 hover:text-blue-700 active:scale-95 transition-all text-center"
          >
            {c.label}
          </button>
        ))}
      </div>
    </div>
  );
}

// ── Date picker ────────────────────────────────────────────────────────

function DatePicker({ onSelect }) {
  const today     = new Date();
  const [showPicker, setShowPicker] = useState(false);

  const presets = [
    { label: "Today",        value: format(today, "yyyy-MM-dd"),           sub: format(today, "EEE, d MMM") },
    { label: "Yesterday",    value: format(subDays(today, 1), "yyyy-MM-dd"), sub: format(subDays(today, 1), "EEE, d MMM") },
    { label: "2 days ago",   value: format(subDays(today, 2), "yyyy-MM-dd"), sub: format(subDays(today, 2), "EEE, d MMM") },
  ];

  return (
    <div className="px-4 pb-4 space-y-2">
      {presets.map((p) => (
        <button
          key={p.value}
          onClick={() => onSelect(p.value, p.label + " · " + p.sub)}
          className="w-full flex items-center justify-between bg-white border border-slate-200 rounded-xl px-4 py-3 hover:border-blue-400 hover:bg-blue-50 active:scale-[0.98] transition-all"
        >
          <div className="text-left">
            <p className="text-sm font-semibold text-slate-700">{p.label}</p>
            <p className="text-xs text-slate-400">{p.sub}</p>
          </div>
          <ChevronRight size={15} className="text-slate-400" />
        </button>
      ))}
      {/* Custom date */}
      <div className="relative">
        <button
          onClick={() => setShowPicker(!showPicker)}
          className="w-full flex items-center justify-between bg-white border border-slate-200 rounded-xl px-4 py-3 hover:border-blue-400 hover:bg-blue-50 active:scale-[0.98] transition-all"
        >
          <div className="flex items-center gap-2 text-left">
            <Calendar size={15} className="text-slate-400" />
            <p className="text-sm font-semibold text-slate-700">Pick a date</p>
          </div>
          <ChevronRight size={15} className="text-slate-400" />
        </button>
        {showPicker && (
          <input
            type="date"
            max={format(today, "yyyy-MM-dd")}
            className="absolute inset-0 opacity-0 w-full cursor-pointer"
            onChange={(e) => {
              if (e.target.value) {
                const d = new Date(e.target.value + "T00:00:00");
                onSelect(e.target.value, format(d, "EEE, d MMM yyyy"));
              }
            }}
          />
        )}
      </div>
    </div>
  );
}

// ── Photo upload step ──────────────────────────────────────────────────

function PhotoStep({ onPhoto, onSkip, uploading }) {
  const inputRef = useRef(null);

  const handleFile = (file) => {
    if (!file) return;
    if (file.size > 10 * 1024 * 1024) { toast.error("File must be under 10 MB."); return; }
    onPhoto(file);
  };

  return (
    <div className="px-4 pb-4 space-y-2">
      <button
        onClick={() => inputRef.current?.click()}
        disabled={uploading}
        className="w-full flex items-center gap-3 bg-blue-700 text-white rounded-xl px-4 py-3.5 font-semibold active:scale-[0.98] transition-all disabled:opacity-60"
      >
        {uploading ? <Loader2 size={18} className="animate-spin" /> : <Camera size={18} />}
        {uploading ? "Uploading photo…" : "Take / Choose Photo"}
      </button>
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        capture="environment"
        className="hidden"
        onChange={(e) => handleFile(e.target.files[0])}
      />
      <button
        onClick={onSkip}
        disabled={uploading}
        className="w-full py-3 text-sm font-semibold text-slate-500 hover:text-slate-700 transition-colors"
      >
        Skip for now →
      </button>
    </div>
  );
}

// ── Notes input ────────────────────────────────────────────────────────

function NotesInput({ onSubmit, onSkip }) {
  const [val, setVal] = useState("");
  return (
    <div className="px-4 pb-4 space-y-2">
      <textarea
        value={val}
        onChange={(e) => setVal(e.target.value)}
        placeholder="e.g. 'Chai stall, morning shift'"
        rows={2}
        maxLength={100}
        className="w-full input-base resize-none text-sm"
        autoFocus
      />
      <div className="flex gap-2">
        <button
          onClick={() => val.trim() && onSubmit(val.trim())}
          disabled={!val.trim()}
          className="flex-1 btn-primary text-sm disabled:opacity-40"
        >
          Add Note
        </button>
        <button onClick={onSkip} className="flex-1 btn-outline text-sm">
          Skip
        </button>
      </div>
    </div>
  );
}

// ── OCR conflict picker ────────────────────────────────────────────────

function OcrConflictPicker({ entered, ocr, onChoose }) {
  return (
    <div className="px-4 pb-4 space-y-2">
      <button
        onClick={() => onChoose(ocr, `₹${Number(ocr).toLocaleString("en-IN")} (from photo)`)}
        className="w-full flex items-center justify-between bg-green-50 border border-green-300 rounded-xl px-4 py-3 hover:bg-green-100 active:scale-[0.98] transition-all"
      >
        <div>
          <p className="text-sm font-bold text-green-800">{formatINR(ocr)}</p>
          <p className="text-xs text-green-600">Amount from photo scan</p>
        </div>
        <ShieldCheck size={18} className="text-green-600" />
      </button>
      <button
        onClick={() => onChoose(entered, `₹${Number(entered).toLocaleString("en-IN")} (I entered)`)}
        className="w-full flex items-center justify-between bg-white border border-slate-200 rounded-xl px-4 py-3 hover:bg-slate-50 active:scale-[0.98] transition-all"
      >
        <div>
          <p className="text-sm font-bold text-slate-700">{formatINR(entered)}</p>
          <p className="text-xs text-slate-400">Amount I entered</p>
        </div>
        <ChevronRight size={15} className="text-slate-400" />
      </button>
    </div>
  );
}

// ── Warning confirm ────────────────────────────────────────────────────

function WarnConfirm({ warnings, onProceed, onEdit }) {
  return (
    <div className="px-4 pb-4 space-y-3">
      <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-3 space-y-1.5">
        {warnings.map((w, i) => (
          <div key={i} className="flex items-start gap-2">
            <AlertTriangle size={13} className="text-yellow-500 shrink-0 mt-0.5" />
            <p className="text-xs text-yellow-800">{w.message}</p>
          </div>
        ))}
      </div>
      <button onClick={onProceed} className="w-full btn-primary text-sm">
        Yes, save anyway
      </button>
      <button onClick={onEdit} className="w-full btn-outline text-sm">
        Edit amount
      </button>
    </div>
  );
}

// ── Success actions ────────────────────────────────────────────────────

function SuccessActions({ onReset, type }) {
  const router = useRouter();
  return (
    <div className="px-4 pb-4 space-y-2">
      <button
        onClick={onReset}
        className={`w-full py-3.5 rounded-xl font-bold text-white text-sm active:scale-[0.98] transition-all ${
          type === "sale" ? "bg-green-600" : "bg-red-500"
        }`}
      >
        + Add Another Entry
      </button>
      <button
        onClick={() => router.push("/transactions")}
        className="w-full btn-outline text-sm"
      >
        View History
      </button>
      <button
        onClick={() => router.push("/home")}
        className="w-full text-sm font-medium text-slate-500 py-2 hover:text-slate-700"
      >
        Go Home
      </button>
    </div>
  );
}

// ── Main chat component ────────────────────────────────────────────────

function ChatFlow({ initialType }) {
  const router       = useRouter();
  const { user }     = useAuthStore();
  const name         = user?.name?.split(" ")[0] || "there";

  const [step,       setStep]       = useState(STEPS.GREETING);
  const [messages,   setMessages]   = useState([]);
  const [showTyping, setShowTyping] = useState(false);
  const [amount,     setAmount]     = useState("");
  const [txType,     setTxType]     = useState(initialType || null);
  const [category,   setCategory]   = useState(null);
  const [date,       setDate]       = useState(format(new Date(), "yyyy-MM-dd"));
  const [dateLabel,  setDateLabel]  = useState("Today");
  const [notes,      setNotes]      = useState("");
  const [photoFile,  setPhotoFile]  = useState(null);
  const [photoPreviewUrl, setPhotoPreviewUrl] = useState(null);
  const [evidenceId, setEvidenceId] = useState(null);
  const [ocrConflict, setOcrConflict] = useState(null);  // { entered, ocr, evidenceId }
  const [warnings,   setWarnings]   = useState([]);
  const [uploading,  setUploading]  = useState(false);
  const [isOffline,  setIsOffline]  = useState(false);

  const bottomRef  = useRef(null);
  const msgIdRef   = useRef(0);

  // ── scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, showTyping]);

  // ── offline detection
  useEffect(() => {
    const onOnline  = () => setIsOffline(false);
    const onOffline = () => setIsOffline(true);
    window.addEventListener("online",  onOnline);
    window.addEventListener("offline", onOffline);
    setIsOffline(!navigator.onLine);
    return () => {
      window.removeEventListener("online",  onOnline);
      window.removeEventListener("offline", onOffline);
    };
  }, []);

  const addMsg = useCallback((msg) => {
    setMessages((prev) => [...prev, { ...msg, id: ++msgIdRef.current }]);
  }, []);

  const botSay = useCallback((text, extra = {}) => {
    return new Promise((resolve) => {
      setShowTyping(true);
      setTimeout(() => {
        setShowTyping(false);
        addMsg({ from: "bot", text, ...extra });
        resolve();
      }, 400);
    });
  }, [addMsg]);

  const userSay = useCallback((text, extra = {}) => {
    addMsg({ from: "user", text, ...extra });
  }, [addMsg]);

  // ── Init greeting
  useEffect(() => {
    const h = new Date().getHours();
    const time = h < 12 ? "morning" : h < 17 ? "afternoon" : "evening";
    const welcomeText = initialType
      ? `Good ${time}, ${name}! Let's record a quick ${initialType}.`
      : `Good ${time}, ${name}! 👋 What would you like to record today?`;

    botSay(welcomeText).then(() => {
      if (initialType) {
        setTxType(initialType);
        setStep(STEPS.AMOUNT);
        botSay(initialType === "sale"
          ? "How much were your total sales?"
          : "How much did you spend?"
        );
      } else {
        setStep(STEPS.GREETING);
      }
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Greeting: user picks type
  const handleTypeSelect = (type) => {
    setTxType(type);
    userSay(type === "sale" ? "Add Sale 🟢" : "Add Expense 🔴");
    setStep(STEPS.AMOUNT);
    botSay(type === "sale"
      ? "How much were your total sales?"
      : "How much did you spend?"
    );
  };

  // ── Amount confirmed
  const handleAmountConfirm = async (val) => {
    const num = parseFloat(val);
    setAmount(val);
    userSay(formatINR(num));
    setStep(STEPS.CATEGORY);
    await botSay(`Got it — ${formatINR(num)}! What was this ${txType === "sale" ? "sale" : "expense"} for?`);
  };

  // ── Category selected
  const handleCategorySelect = async (cat) => {
    setCategory(cat);
    userSay(cat.label);
    setStep(STEPS.DATE);
    await botSay("When did this happen?");
  };

  // ── Date selected
  const handleDateSelect = async (val, label) => {
    setDate(val);
    setDateLabel(label);
    userSay(label);
    setStep(STEPS.PHOTO);
    await botSay("Would you like to add a bill photo? It strengthens your evidence and helps with compliance.");
  };

  // ── Photo upload
  const handlePhotoUpload = async (file) => {
    setPhotoFile(file);
    const previewUrl = URL.createObjectURL(file);
    setPhotoPreviewUrl(previewUrl);
    userSay("", { type: "photo_preview", src: previewUrl, ocrStatus: "pending" });
    setUploading(true);

    try {
      const res = await evidenceApi.upload(file);
      const ev  = res.data.data;
      setEvidenceId(ev.evidence_id);

      // Update photo bubble OCR status
      setMessages((prev) =>
        prev.map((m) =>
          m.type === "photo_preview" ? { ...m, ocrStatus: ev.ocr_status } : m
        )
      );

      if (ev.quality_status === "rejected") {
        await botSay("The photo quality is too low to scan. I'll save your entry without it.");
        setPhotoFile(null);
        setEvidenceId(null);
        setStep(STEPS.NOTES);
        await botSay("Any short note to add? (optional)");
        return;
      }

      // Poll for OCR completion
      let ocrResult = ev;
      if (ev.ocr_status === "pending" || ev.ocr_status === "processing") {
        await botSay("Scanning your receipt… just a moment!");
        let attempts = 0;
        while (attempts < 8 && (ocrResult.ocr_status === "pending" || ocrResult.ocr_status === "processing")) {
          await new Promise((r) => setTimeout(r, 2500));
          try {
            const poll = await evidenceApi.get(ev.evidence_id);
            ocrResult  = poll.data.data;
          } catch { break; }
          attempts++;
        }

        setMessages((prev) =>
          prev.map((m) =>
            m.type === "photo_preview" ? { ...m, ocrStatus: ocrResult.ocr_status } : m
          )
        );
      }

      // Check OCR conflict
      if (
        ocrResult.ocr_status === "success" &&
        ocrResult.ocr_amount != null &&
        Math.abs(ocrResult.ocr_amount - parseFloat(amount)) / parseFloat(amount) > 0.05
      ) {
        setOcrConflict({ entered: parseFloat(amount), ocr: ocrResult.ocr_amount, evidenceId: ev.evidence_id });
        setStep(STEPS.OCR_CONFLICT);
        await botSay(
          `The receipt shows ${formatINR(ocrResult.ocr_amount)}, but you entered ${formatINR(parseFloat(amount))}. Which is correct?`
        );
        return;
      }

      if (ocrResult.ocr_status === "success") {
        await botSay(`Receipt scanned! I found ${ocrResult.ocr_vendor_name ? `"${ocrResult.ocr_vendor_name}"` : "a valid receipt"}.`);
      } else if (ocrResult.ocr_status === "failed") {
        await botSay("Couldn't read the receipt clearly, but I've saved the photo as supporting evidence.");
      }

    } catch (err) {
      toast.error(getApiError(err));
    } finally {
      setUploading(false);
    }

    setStep(STEPS.NOTES);
    await botSay("Any note to add? (optional)");
  };

  const handlePhotoSkip = async () => {
    userSay("Skip for now →");
    setStep(STEPS.NOTES);
    await botSay("Any note to add? (optional)");
  };

  // ── OCR conflict resolved
  const handleOcrResolve = async (resolvedAmount, label) => {
    setAmount(String(resolvedAmount));
    userSay(label);
    // If user picked a different amount, patch the transaction later
    setOcrConflict((prev) => ({ ...prev, resolvedAmount }));
    setStep(STEPS.NOTES);
    await botSay("Any note to add? (optional)");
  };

  // ── Notes
  const handleNotesSubmit = async (val) => {
    setNotes(val);
    userSay(val);
    await proceedToConfirm(val);
  };

  const handleNotesSkip = async () => {
    userSay("Skip →");
    await proceedToConfirm("");
  };

  const proceedToConfirm = async (n) => {
    setStep(STEPS.CONFIRM);
    const catLabel = category?.label || "—";
    await botSay("", {
      type: "summary_card",
      meta: {
        type:          txType,
        amount:        amount,
        category:      category?.value,
        categoryLabel: catLabel,
        dateLabel,
        hasPhoto:      !!evidenceId,
        notes:         n,
      },
    });
  };

  // ── Confirm: run validation then submit
  const handleConfirm = async () => {
    setStep(STEPS.SUBMITTING);
    setShowTyping(true);

    // Validation
    try {
      const vRes = await validationApi.check({ amount: parseFloat(amount), type: txType, transaction_date: date });
      const warns = vRes.data.data.warnings || [];
      if (warns.length > 0 && !vRes.data.data.valid === false) {
        // Show warning, ask to confirm
        setWarnings(warns);
        setShowTyping(false);
        setStep(STEPS.WARN_CONFIRM);
        await botSay(`⚠️ Just a heads-up before I save:`);
        return;
      }
    } catch {
      // validation failure shouldn't block submit
    }

    await submitTransaction();
  };

  const handleWarnProceed = async () => {
    userSay("Yes, save anyway");
    setStep(STEPS.SUBMITTING);
    await submitTransaction();
  };

  const handleWarnEdit = async () => {
    userSay("Let me edit the amount");
    setMessages([]);
    setAmount("");
    setCategory(null);
    setDate(format(new Date(), "yyyy-MM-dd"));
    setDateLabel("Today");
    setNotes("");
    setPhotoFile(null);
    setPhotoPreviewUrl(null);
    setEvidenceId(null);
    setOcrConflict(null);
    setWarnings([]);
    setStep(STEPS.AMOUNT);
    await botSay(`No problem! How much was the ${txType === "sale" ? "sale" : "expense"}?`);
  };

  const submitTransaction = async () => {
    if (isOffline) {
      toast.error("You are offline. Please reconnect and try again.");
      setStep(STEPS.CONFIRM);
      setShowTyping(false);
      return;
    }

    try {
      const payload = {
        type:             txType,
        amount:           parseFloat(amount),
        category:         category?.value || null,
        transaction_date: date,
        description:      notes || null,
      };

      const res = photoFile
        ? await transactionsApi.create(payload, photoFile)
        : await transactionsApi.create(payload);

      const tx = res.data.data?.transaction;

      // If OCR conflict and user chose a different amount, patch it
      if (ocrConflict && ocrConflict.resolvedAmount !== ocrConflict.ocr) {
        try {
          await transactionsApi.confirmAmount(tx.id, parseFloat(amount));
        } catch { /* non-fatal */ }
      }

      setShowTyping(false);
      setStep(STEPS.SUCCESS);
      const emoji = txType === "sale" ? "🟢" : "🔴";
      await botSay(`${emoji} Done! ${formatINR(parseFloat(amount))} ${txType} saved successfully. Your record is up to date.`);

    } catch (err) {
      setShowTyping(false);
      toast.error(getApiError(err));
      setStep(STEPS.CONFIRM);
      addMsg({ from: "bot", text: "Something went wrong. Please tap Confirm to try again." });
    }
  };

  // ── Reset for "add another"
  const handleReset = () => {
    setMessages([]);
    setStep(STEPS.GREETING);
    setAmount(""); setTxType(initialType || null);
    setCategory(null);
    setDate(format(new Date(), "yyyy-MM-dd")); setDateLabel("Today");
    setNotes(""); setPhotoFile(null); setPhotoPreviewUrl(null);
    setEvidenceId(null); setOcrConflict(null); setWarnings([]);

    const h = new Date().getHours();
    const time = h < 12 ? "morning" : h < 17 ? "afternoon" : "evening";
    if (initialType) {
      setTxType(initialType);
      setStep(STEPS.AMOUNT);
      botSay(initialType === "sale"
        ? `Great! What were your sales this time?`
        : `What did you spend this time?`
      );
    } else {
      botSay(`What would you like to record next?`).then(() => setStep(STEPS.GREETING));
    }
  };

  // ── Render current input area
  const renderInput = () => {
    switch (step) {
      case STEPS.GREETING:
        return (
          <div className="px-4 pb-4 grid grid-cols-2 gap-3">
            <button
              onClick={() => handleTypeSelect("sale")}
              className="flex flex-col items-center gap-2 bg-green-600 text-white rounded-2xl py-4 font-bold active:scale-95 transition-all shadow-sm"
            >
              <TrendingUp size={22} />
              <span className="text-sm">Add Sale</span>
            </button>
            <button
              onClick={() => handleTypeSelect("expense")}
              className="flex flex-col items-center gap-2 bg-red-500 text-white rounded-2xl py-4 font-bold active:scale-95 transition-all shadow-sm"
            >
              <TrendingDown size={22} />
              <span className="text-sm">Add Expense</span>
            </button>
          </div>
        );

      case STEPS.AMOUNT:
        return (
          <AmountInput
            value={amount}
            onChange={setAmount}
            onConfirm={handleAmountConfirm}
            type={txType}
          />
        );

      case STEPS.CATEGORY:
        return <CategoryPicker type={txType} onSelect={handleCategorySelect} />;

      case STEPS.DATE:
        return <DatePicker onSelect={handleDateSelect} />;

      case STEPS.PHOTO:
        return <PhotoStep onPhoto={handlePhotoUpload} onSkip={handlePhotoSkip} uploading={uploading} />;

      case STEPS.NOTES:
        return <NotesInput onSubmit={handleNotesSubmit} onSkip={handleNotesSkip} />;

      case STEPS.CONFIRM:
        return (
          <div className="px-4 pb-4 space-y-2">
            <button onClick={handleConfirm} className="w-full btn-primary flex items-center justify-center gap-2">
              <CheckCircle2 size={16} /> Save Entry
            </button>
            <button onClick={handleWarnEdit} className="w-full btn-outline text-sm">
              Edit
            </button>
          </div>
        );

      case STEPS.OCR_CONFLICT:
        return (
          <OcrConflictPicker
            entered={ocrConflict?.entered}
            ocr={ocrConflict?.ocr}
            onChoose={handleOcrResolve}
          />
        );

      case STEPS.WARN_CONFIRM:
        return (
          <WarnConfirm
            warnings={warnings}
            onProceed={handleWarnProceed}
            onEdit={handleWarnEdit}
          />
        );

      case STEPS.SUBMITTING:
        return (
          <div className="px-4 pb-4 flex items-center justify-center py-6 gap-3">
            <Loader2 size={20} className="animate-spin text-blue-700" />
            <span className="text-sm font-medium text-slate-600">Saving your entry…</span>
          </div>
        );

      case STEPS.SUCCESS:
        return <SuccessActions onReset={handleReset} type={txType} />;

      default:
        return null;
    }
  };

  return (
    <div className="flex flex-col h-screen bg-slate-50">
      {/* ── Header */}
      <header className="sticky top-0 z-20 bg-white border-b border-slate-200 px-4 h-14 flex items-center gap-3">
        <button onClick={() => router.back()} className="p-1.5 -ml-1 text-slate-500 hover:text-slate-800">
          <ArrowLeft size={20} />
        </button>
        <div className="flex items-center gap-2 flex-1">
          <div className="w-8 h-8 rounded-full bg-blue-700 flex items-center justify-center">
            <Sparkles size={14} className="text-white" />
          </div>
          <div>
            <p className="text-sm font-bold text-slate-800 leading-none">BharatBot</p>
            <p className="text-xs text-green-500 font-medium">Online</p>
          </div>
        </div>
        {txType && (
          <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${
            txType === "sale"
              ? "bg-green-100 text-green-700"
              : "bg-red-100 text-red-700"
          }`}>
            {txType === "sale" ? "Sale" : "Expense"}
          </span>
        )}
      </header>

      {/* ── Offline banner */}
      {isOffline && (
        <div className="bg-yellow-500 text-white text-xs font-semibold text-center py-1.5 px-4">
          You are offline — data will sync when you reconnect
        </div>
      )}

      {/* ── Messages area */}
      <div className="flex-1 overflow-y-auto py-3 space-y-1">
        <style>{`
          @keyframes msgIn {
            from { opacity: 0; transform: translateY(10px); }
            to   { opacity: 1; transform: translateY(0); }
          }
          .msg-in { animation: msgIn 0.22s ease-out; }
        `}</style>

        {messages.map((msg) => (
          <ChatMessage key={msg.id} msg={msg} />
        ))}

        {showTyping && <TypingDots />}
        <div ref={bottomRef} />
      </div>

      {/* ── Input area */}
      <div className="bg-white border-t border-slate-200 pt-3">
        {renderInput()}
      </div>
    </div>
  );
}

// ── Suspense wrapper for useSearchParams ──────────────────────────────

function ChatWithParams() {
  const params      = useSearchParams();
  const initialType = params.get("type"); // "sale" | "expense" | null
  return <ChatFlow initialType={initialType} />;
}

export default function NewTransactionPage() {
  return (
    <Suspense fallback={<div className="h-screen flex items-center justify-center"><Loader2 size={24} className="animate-spin text-blue-700" /></div>}>
      <ChatWithParams />
    </Suspense>
  );
}
