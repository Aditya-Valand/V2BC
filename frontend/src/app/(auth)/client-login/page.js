"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Smartphone, Lock, Eye, EyeOff, ArrowRight } from "lucide-react";
import { toast } from "sonner";
import { authApi } from "@/lib/api/auth";
import { getApiError } from "@/lib/api/client";
import useAuthStore from "@/store/authStore";

export default function ClientLoginPage() {
  const router   = useRouter();
  const setAuth  = useAuthStore((s) => s.setAuth);

  const [phone,      setPhone]      = useState("");
  const [pin,        setPin]        = useState("");
  const [showPin,    setShowPin]    = useState(false);
  const [loading,    setLoading]    = useState(false);
  const [fieldError, setFieldError] = useState({});

  const validate = () => {
    const errs = {};
    const digits = phone.replace(/\D/g, "");
    if (!digits || digits.length < 10)
      errs.phone = "Enter a valid 10-digit mobile number.";
    if (!pin || pin.length < 4)
      errs.pin = "Enter your 4–6 digit PIN.";
    return errs;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const errs = validate();
    if (Object.keys(errs).length) { setFieldError(errs); return; }
    setFieldError({});
    setLoading(true);

    try {
      const res = await authApi.clientLogin(phone.trim(), pin);
      const { access_token, refresh_token, user, org } = res.data.data;
      setAuth({ access_token, refresh_token, user, org });
      toast.success(`Welcome back, ${user.name?.split(" ")[0]}!`);
      router.replace("/home");
    } catch (err) {
      const msg = getApiError(err);
      if (typeof msg === "string") {
        toast.error(msg);
      } else {
        setFieldError(msg);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full max-w-sm mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8 text-center">
        <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-blue-700 mb-4">
          <Smartphone size={26} color="white" />
        </div>
        <h1 className="text-2xl font-bold text-slate-800">Client Login</h1>
        <p className="text-sm text-slate-500 mt-1">Enter your phone number and PIN</p>
      </div>

      <form onSubmit={handleSubmit} noValidate className="space-y-4">
        {/* Phone */}
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            Mobile Number
          </label>
          <div className="relative">
            <Smartphone
              size={16}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none"
            />
            <input
              type="tel"
              inputMode="numeric"
              placeholder="9XXXXXXXXX"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              className={`input-base pl-9 ${fieldError.phone ? "error" : ""}`}
              autoComplete="tel"
            />
          </div>
          {fieldError.phone && (
            <p className="text-xs text-red-500 mt-1">{fieldError.phone}</p>
          )}
        </div>

        {/* PIN */}
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            PIN
          </label>
          <div className="relative">
            <Lock
              size={16}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none"
            />
            <input
              type={showPin ? "text" : "password"}
              inputMode="numeric"
              placeholder="4–6 digit PIN"
              value={pin}
              onChange={(e) => setPin(e.target.value)}
              maxLength={6}
              className={`input-base pl-9 pr-10 ${fieldError.pin ? "error" : ""}`}
              autoComplete="current-password"
            />
            <button
              type="button"
              onClick={() => setShowPin((v) => !v)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
              tabIndex={-1}
            >
              {showPin ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
          </div>
          {fieldError.pin && (
            <p className="text-xs text-red-500 mt-1">{fieldError.pin}</p>
          )}
        </div>

        {/* Submit */}
        <button
          type="submit"
          disabled={loading}
          className="btn-primary w-full mt-2"
        >
          {loading ? "Logging in…" : (
            <>Login <ArrowRight size={16} /></>
          )}
        </button>
      </form>

      {/* Divider */}
      <div className="flex items-center gap-3 my-6">
        <div className="flex-1 h-px bg-slate-200" />
        <span className="text-xs text-slate-400">or</span>
        <div className="flex-1 h-px bg-slate-200" />
      </div>

      {/* CA login link */}
      <p className="text-center text-sm text-slate-500">
        Are you a CA?{" "}
        <Link href="/login" className="text-blue-700 font-semibold hover:underline">
          CA Login
        </Link>
      </p>

      {/* Help text */}
      <p className="text-center text-xs text-slate-400 mt-4">
        New here? Ask your CA to send you an invite link.
      </p>
    </div>
  );
}
