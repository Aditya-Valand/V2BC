"use client";

import { useState, useEffect } from "react";
import { useRouter, useParams } from "next/navigation";
import { toast } from "sonner";
import {
  Building2, User, Phone, Lock, Eye, EyeOff,
  ArrowRight, Loader2, CheckCircle2, AlertCircle,
} from "lucide-react";
import { inviteApi } from "@/lib/api/clients";
import { getApiError } from "@/lib/api/client";
import useAuthStore from "@/store/authStore";

/* ── Stage 1: Preview invite ──────────────────────────────────── */
function InvitePreview({ invite, onAccept }) {
  return (
    <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-8 text-center">
      <div className="w-16 h-16 bg-blue-50 rounded-2xl flex items-center justify-center mx-auto mb-5">
        <Building2 size={28} className="text-blue-700" />
      </div>

      <p className="text-slate-500 text-sm mb-1">You&apos;ve been invited by</p>
      <h2 className="text-xl font-bold text-slate-800 mb-1">{invite.ca_firm_name}</h2>
      <p className="text-slate-500 text-sm mb-6">
        to manage compliance for <span className="font-semibold text-slate-700">{invite.client_name}</span>
      </p>

      <div className="bg-slate-50 rounded-xl p-4 mb-6 text-left space-y-2">
        {[
          "Track GST & compliance deadlines",
          "Log daily sales and expenses easily",
          "Receive reminders on WhatsApp",
        ].map((item) => (
          <div key={item} className="flex items-center gap-2 text-sm text-slate-600">
            <CheckCircle2 size={15} className="text-green-500 shrink-0" />
            {item}
          </div>
        ))}
      </div>

      <button onClick={onAccept} className="btn-primary w-full">
        Accept Invitation <ArrowRight size={16} />
      </button>

      <p className="text-xs text-slate-400 mt-4">
        Free for you — your CA firm manages billing.
      </p>
    </div>
  );
}

/* ── Stage 2: Accept form ─────────────────────────────────────── */
function AcceptForm({ invite, onSuccess }) {
  const [form, setForm] = useState({ name: "", phone: "", pin: "", showPin: false });
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);

  const set = (field) => (e) => {
    setForm((f) => ({ ...f, [field]: e.target.value }));
    if (errors[field]) setErrors((er) => ({ ...er, [field]: null }));
  };

  const validate = () => {
    const e = {};
    if (!form.name.trim() || form.name.trim().length < 2) e.name = "Name must be at least 2 characters";
    if (!form.phone || !/^[6-9]\d{9}$/.test(form.phone)) e.phone = "Enter valid 10-digit mobile number";
    if (!form.pin || !/^\d{4,6}$/.test(form.pin)) e.pin = "PIN must be 4-6 digits";
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validate()) return;
    setLoading(true);
    try {
      const res = await inviteApi.accept({
        invite_code: invite.invite_code,
        name:        form.name.trim(),
        phone:       form.phone,
        pin:         form.pin,
      });
      const { user_id, otp_dev_only } = res.data.data;
      if (otp_dev_only) toast.info(`DEV OTP: ${otp_dev_only}`, { duration: 20000 });
      toast.success("Invite accepted! Check your phone for the OTP.");
      onSuccess(user_id, form.phone);
    } catch (err) {
      const status = err.response?.status;
      if (status === 410) {
        toast.error("This invite link has expired. Ask your CA for a new one.");
      } else if (status === 409) {
        toast.error("This invite has already been accepted. Try logging in.");
      } else {
        toast.error(getApiError(err));
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-8">
      <div className="mb-6">
        <p className="text-xs font-semibold text-blue-700 uppercase tracking-wide mb-1">
          {invite.ca_firm_name}
        </p>
        <h1 className="text-2xl font-bold text-slate-800">Create your account</h1>
        <p className="text-slate-500 text-sm mt-1">For {invite.client_name}</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1.5">Your Name</label>
          <div className="relative">
            <User size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
            <input value={form.name} onChange={set("name")} placeholder="Ram Prasad"
              className={`input-base pl-10 ${errors.name ? "error" : ""}`} />
          </div>
          {errors.name && <p className="text-red-500 text-xs mt-1">{errors.name}</p>}
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1.5">Mobile Number</label>
          <div className="relative">
            <div className="absolute left-3.5 top-1/2 -translate-y-1/2 flex items-center gap-1.5">
              <Phone size={14} className="text-slate-400" />
              <span className="text-slate-500 text-sm font-medium">+91</span>
            </div>
            <input value={form.phone} onChange={set("phone")} placeholder="9876543210"
              inputMode="numeric" maxLength={10}
              className={`input-base pl-14 ${errors.phone ? "error" : ""}`} />
          </div>
          {errors.phone && <p className="text-red-500 text-xs mt-1">{errors.phone}</p>}
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1.5">
            Set PIN <span className="text-slate-400 font-normal">(4-6 digits — used to log in)</span>
          </label>
          <div className="relative">
            <Lock size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type={form.showPin ? "text" : "password"}
              inputMode="numeric"
              maxLength={6}
              value={form.pin}
              onChange={set("pin")}
              placeholder="e.g. 1234"
              className={`input-base pl-10 pr-10 ${errors.pin ? "error" : ""}`}
            />
            <button type="button" onClick={() => setForm((f) => ({ ...f, showPin: !f.showPin }))}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600">
              {form.showPin ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
          </div>
          {errors.pin && <p className="text-red-500 text-xs mt-1">{errors.pin}</p>}
        </div>

        <button type="submit" disabled={loading} className="btn-primary w-full mt-2">
          {loading ? <><Loader2 size={16} className="animate-spin" /> Please wait...</> : <>Continue <ArrowRight size={16} /></>}
        </button>
      </form>
    </div>
  );
}

/* ── Stage 3: OTP verification (client) ──────────────────────── */
function ClientOtpVerify({ userId, phone, onSuccess }) {
  const [otp, setOtp]       = useState(["", "", "", "", "", ""]);
  const [loading, setLoad]  = useState(false);
  const [countdown, setCD]  = useState(60);
  const inputRefs           = useRef([]);

  const inputRefs2 = useState([])[0]; // avoid eslint issue
  const refs = Array.from({ length: 6 }, (_, i) => i);

  useEffect(() => {
    if (countdown <= 0) return;
    const t = setTimeout(() => setCD((n) => n - 1), 1000);
    return () => clearTimeout(t);
  }, [countdown]);

  const setRef = (i) => (el) => {
    if (!inputRefs.current) inputRefs.current = [];
    inputRefs.current[i] = el;
  };

  const handleChange = (i, val) => {
    if (val.length > 1) {
      const digits = val.replace(/\D/g, "").slice(0, 6).split("");
      const next = [...otp];
      digits.forEach((d, di) => { if (di < 6) next[di] = d; });
      setOtp(next);
      inputRefs.current[Math.min(digits.length, 5)]?.focus();
      return;
    }
    if (!/^\d?$/.test(val)) return;
    const next = [...otp]; next[i] = val; setOtp(next);
    if (val && i < 5) inputRefs.current[i + 1]?.focus();
  };

  const handleKeyDown = (i, e) => {
    if (e.key === "Backspace" && !otp[i] && i > 0) inputRefs.current[i - 1]?.focus();
  };

  const handleVerify = async () => {
    const code = otp.join("");
    if (code.length !== 6) { toast.error("Enter the 6-digit code"); return; }
    setLoad(true);
    try {
      const res = await inviteApi.verifyOtp(userId, code);
      onSuccess(res.data.data);
    } catch (err) {
      toast.error(getApiError(err));
      setOtp(["", "", "", "", "", ""]);
      inputRefs.current[0]?.focus();
    } finally {
      setLoad(false);
    }
  };

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-8 text-center">
      <div className="w-16 h-16 bg-green-50 rounded-2xl flex items-center justify-center mx-auto mb-5">
        <Phone size={28} className="text-green-600" />
      </div>
      <h1 className="text-2xl font-bold text-slate-800 mb-2">Verify your number</h1>
      <p className="text-slate-500 text-sm">
        OTP sent to <span className="font-semibold text-slate-700">+91 {phone}</span>
      </p>

      <div className="flex justify-center gap-2.5 mt-8 mb-6">
        {otp.map((digit, i) => (
          <input key={i} ref={(el) => { if (!inputRefs.current) inputRefs.current = []; inputRefs.current[i] = el; }}
            type="text" inputMode="numeric" maxLength={6} value={digit}
            onChange={(e) => handleChange(i, e.target.value)}
            onKeyDown={(e) => handleKeyDown(i, e)}
            className={`otp-input w-11 h-12 text-center text-xl font-bold border-2 rounded-xl transition-all
              ${digit ? "border-blue-600 bg-blue-50 text-blue-800" : "border-slate-300 bg-white"}`}
          />
        ))}
      </div>

      <button onClick={handleVerify} disabled={loading || otp.join("").length !== 6} className="btn-primary w-full mb-4">
        {loading ? <><Loader2 size={16} className="animate-spin" /> Verifying...</> : "Verify & Log In"}
      </button>

      <p className="text-sm text-slate-400">
        {countdown > 0 ? `Resend in 0:${String(countdown).padStart(2, "0")}` : (
          <button className="text-blue-700 font-semibold hover:underline">Resend OTP</button>
        )}
      </p>
    </div>
  );
}

/* ── Main page ────────────────────────────────────────────────── */
export default function InvitePage() {
  const params   = useParams();
  const router   = useRouter();
  const setAuth  = useAuthStore((s) => s.setAuth);
  const code     = params.code;

  const [stage, setStage]   = useState("loading"); // loading | preview | accept | otp | expired | error
  const [invite, setInvite] = useState(null);
  const [pendingUserId, setUserId] = useState(null);
  const [pendingPhone, setPhone]   = useState(null);

  useEffect(() => {
    if (!code) return;
    inviteApi.preview(code)
      .then((res) => {
        const data = res.data.data.invite;
        setInvite(data);
        if (data.is_expired || data.invite_status === "expired") {
          setStage("expired");
        } else if (data.invite_status === "active") {
          // Already accepted — direct to login
          setStage("already_active");
        } else {
          setStage("preview");
        }
      })
      .catch(() => setStage("error"));
  }, [code]);

  const handleAcceptSuccess = (userId, phone) => {
    setUserId(userId);
    setPhone(phone);
    setStage("otp");
  };

  const handleOtpSuccess = (data) => {
    setAuth({
      user:          data.user,
      org:           null,
      access_token:  data.access_token,
      refresh_token: data.refresh_token,
    });
    toast.success(`Welcome, ${data.user.name}! 🎉`);
    router.push("/home");
  };

  /* Loading */
  if (stage === "loading") {
    return (
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-12 text-center">
        <Loader2 size={32} className="animate-spin text-blue-600 mx-auto mb-3" />
        <p className="text-slate-500 text-sm">Loading invite...</p>
      </div>
    );
  }

  /* Expired */
  if (stage === "expired") {
    return (
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-8 text-center">
        <div className="w-16 h-16 bg-red-50 rounded-2xl flex items-center justify-center mx-auto mb-5">
          <AlertCircle size={28} className="text-red-500" />
        </div>
        <h2 className="text-xl font-bold text-slate-800 mb-2">Invite link expired</h2>
        <p className="text-slate-500 text-sm">This link is no longer valid. Please contact your CA firm for a new invite.</p>
      </div>
    );
  }

  /* Error */
  if (stage === "error") {
    return (
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-8 text-center">
        <div className="w-16 h-16 bg-red-50 rounded-2xl flex items-center justify-center mx-auto mb-5">
          <AlertCircle size={28} className="text-red-500" />
        </div>
        <h2 className="text-xl font-bold text-slate-800 mb-2">Invalid invite link</h2>
        <p className="text-slate-500 text-sm">This invite link is invalid or does not exist.</p>
      </div>
    );
  }

  if (stage === "already_active") {
    return (
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-8 text-center">
        <div className="w-16 h-16 bg-green-50 rounded-2xl flex items-center justify-center mx-auto mb-5">
          <CheckCircle2 size={28} className="text-green-600" />
        </div>
        <h2 className="text-xl font-bold text-slate-800 mb-2">Already registered</h2>
        <p className="text-slate-500 text-sm mb-6">
          You&apos;ve already accepted this invite. Log in to continue.
        </p>
        <button onClick={() => router.push("/login")} className="btn-primary w-full">
          Go to Login <ArrowRight size={16} />
        </button>
      </div>
    );
  }

  if (stage === "preview") return <InvitePreview invite={invite} onAccept={() => setStage("accept")} />;
  if (stage === "accept")  return <AcceptForm invite={invite} onSuccess={handleAcceptSuccess} />;
  if (stage === "otp")     return <ClientOtpVerify userId={pendingUserId} phone={pendingPhone} onSuccess={handleOtpSuccess} />;

  return null;
}
