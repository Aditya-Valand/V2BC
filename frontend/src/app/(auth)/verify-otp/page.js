"use client";

import { useState, useEffect, useRef, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { toast } from "sonner";
import { Mail, Loader2, RefreshCw, ArrowLeft } from "lucide-react";
import { authApi } from "@/lib/api/auth";
import { getApiError } from "@/lib/api/client";
import useAuthStore from "@/store/authStore";

function VerifyOtpContent() {
  const router   = useRouter();
  const params   = useSearchParams();
  const setAuth  = useAuthStore((s) => s.setAuth);

  const userId   = params.get("user_id");
  const emailHint = params.get("email");

  const [otp, setOtp]               = useState(["", "", "", "", "", ""]);
  const [loading, setLoading]       = useState(false);
  const [resendLoading, setResend]  = useState(false);
  const [countdown, setCountdown]   = useState(60);
  const [shake, setShake]           = useState(false);
  const inputRefs = useRef([]);

  /* Redirect guard */
  useEffect(() => {
    if (!userId) router.replace("/login");
  }, [userId, router]);

  /* Countdown timer */
  useEffect(() => {
    if (countdown <= 0) return;
    const t = setTimeout(() => setCountdown((n) => n - 1), 1000);
    return () => clearTimeout(t);
  }, [countdown]);

  /* Auto-focus first input */
  useEffect(() => {
    inputRefs.current[0]?.focus();
  }, []);

  const handleChange = (i, val) => {
    // Handle paste
    if (val.length > 1) {
      const digits = val.replace(/\D/g, "").slice(0, 6).split("");
      const next = [...otp];
      digits.forEach((d, di) => { if (di < 6) next[di] = d; });
      setOtp(next);
      const lastFilled = Math.min(digits.length, 5);
      inputRefs.current[lastFilled]?.focus();
      return;
    }
    if (!/^\d?$/.test(val)) return;
    const next = [...otp];
    next[i] = val;
    setOtp(next);
    if (val && i < 5) inputRefs.current[i + 1]?.focus();
  };

  const handleKeyDown = (i, e) => {
    if (e.key === "Backspace" && !otp[i] && i > 0) {
      inputRefs.current[i - 1]?.focus();
    }
  };

  const handleVerify = async () => {
    const code = otp.join("");
    if (code.length !== 6) {
      setShake(true);
      setTimeout(() => setShake(false), 600);
      toast.error("Please enter the complete 6-digit OTP");
      return;
    }

    setLoading(true);
    try {
      const res  = await authApi.verifyOtp(userId, code);
      const data = res.data.data;

      setAuth({
        user:          data.user,
        org:           data.org,
        access_token:  data.access_token,
        refresh_token: data.refresh_token,
      });

      toast.success("Email verified! Welcome to BharatCompliance 🎉");
      router.push(data.user.role === "client" ? "/home" : "/dashboard");
    } catch (err) {
      setShake(true);
      setTimeout(() => setShake(false), 600);
      setOtp(["", "", "", "", "", ""]);
      inputRefs.current[0]?.focus();
      toast.error(getApiError(err));
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async () => {
    setResend(true);
    try {
      const res = await authApi.resendOtp(userId);
      const { otp_dev_only } = res.data.data;
      toast.success("New OTP sent to your email!");
      if (otp_dev_only) toast.info(`DEV OTP: ${otp_dev_only}`, { duration: 20000 });
      setCountdown(60);
      setOtp(["", "", "", "", "", ""]);
      inputRefs.current[0]?.focus();
    } catch (err) {
      toast.error(getApiError(err));
    } finally {
      setResend(false);
    }
  };

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-8 text-center">
      {/* Icon */}
      <div className="w-16 h-16 bg-blue-50 rounded-2xl flex items-center justify-center mx-auto mb-5">
        <Mail size={28} className="text-blue-700" />
      </div>

      <h1 className="text-2xl font-bold text-slate-800 mb-2">Check your email</h1>
      <p className="text-slate-500 text-sm leading-relaxed">
        We sent a 6-digit verification code
        {emailHint && (
          <> to <span className="font-semibold text-slate-700">{emailHint}</span></>
        )}
        . It expires in 10 minutes.
      </p>

      {/* OTP boxes */}
      <div
        className={`flex justify-center gap-2.5 mt-8 mb-6 transition-all ${shake ? "animate-bounce" : ""}`}
        style={shake ? { animation: "shake 0.4s ease" } : {}}
      >
        {otp.map((digit, i) => (
          <input
            key={i}
            ref={(el) => (inputRefs.current[i] = el)}
            type="text"
            inputMode="numeric"
            maxLength={6}
            value={digit}
            onChange={(e) => handleChange(i, e.target.value)}
            onKeyDown={(e) => handleKeyDown(i, e)}
            className={`otp-input w-11 h-12 text-center text-xl font-bold border-2 rounded-xl transition-all
              ${digit ? "border-blue-600 bg-blue-50 text-blue-800" : "border-slate-300 bg-white text-slate-800"}`}
          />
        ))}
      </div>

      {/* Verify button */}
      <button
        onClick={handleVerify}
        disabled={loading || otp.join("").length !== 6}
        className="btn-primary w-full mb-5"
      >
        {loading ? (
          <><Loader2 size={16} className="animate-spin" /> Verifying...</>
        ) : (
          "Verify & Continue"
        )}
      </button>

      {/* Resend */}
      <div className="text-sm">
        {countdown > 0 ? (
          <p className="text-slate-400">
            Resend code in{" "}
            <span className="font-semibold text-slate-600 tabular-nums">
              0:{String(countdown).padStart(2, "0")}
            </span>
          </p>
        ) : (
          <button
            onClick={handleResend}
            disabled={resendLoading}
            className="text-blue-700 font-semibold hover:underline inline-flex items-center gap-1.5"
          >
            <RefreshCw size={14} className={resendLoading ? "animate-spin" : ""} />
            {resendLoading ? "Sending..." : "Resend OTP"}
          </button>
        )}
      </div>

      {/* Back */}
      <button
        onClick={() => router.back()}
        className="mt-5 text-slate-400 hover:text-slate-600 text-sm inline-flex items-center gap-1"
      >
        <ArrowLeft size={14} /> Back
      </button>

      {/* Shake animation */}
      <style jsx>{`
        @keyframes shake {
          0%, 100% { transform: translateX(0); }
          20%       { transform: translateX(-8px); }
          40%       { transform: translateX(8px); }
          60%       { transform: translateX(-4px); }
          80%       { transform: translateX(4px); }
        }
      `}</style>
    </div>
  );
}

export default function VerifyOtpPage() {
  return (
    <Suspense fallback={
      <div className="flex justify-center py-20">
        <Loader2 size={32} className="animate-spin text-blue-600" />
      </div>
    }>
      <VerifyOtpContent />
    </Suspense>
  );
}
