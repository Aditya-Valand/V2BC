"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import { Eye, EyeOff, Mail, Lock, ArrowRight, Loader2 } from "lucide-react";
import { authApi } from "@/lib/api/auth";
import { getApiError } from "@/lib/api/client";
import useAuthStore from "@/store/authStore";

export default function LoginPage() {
  const router = useRouter();
  const setAuth = useAuthStore((s) => s.setAuth);

  const [form, setForm]         = useState({ email: "", password: "" });
  const [showPass, setShowPass] = useState(false);
  const [loading, setLoading]   = useState(false);
  const [errors, setErrors]     = useState({});

  const set = (field) => (e) => {
    setForm((f) => ({ ...f, [field]: e.target.value }));
    if (errors[field]) setErrors((er) => ({ ...er, [field]: null }));
  };

  const validate = () => {
    const e = {};
    if (!form.email)    e.email    = "Email is required";
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) e.email = "Enter a valid email";
    if (!form.password) e.password = "Password is required";
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleSubmit = async (evt) => {
    evt.preventDefault();
    if (!validate()) return;

    setLoading(true);
    try {
      const res  = await authApi.login(form.email, form.password);
      const data = res.data.data;

      setAuth({
        user:          data.user,
        org:           data.org,
        access_token:  data.access_token,
        refresh_token: data.refresh_token,
      });

      toast.success(`Welcome back, ${data.user.name}!`);
      router.push(data.user.role === "client" ? "/home" : "/dashboard");
    } catch (err) {
      const status = err.response?.status;
      if (status === 403) {
        toast.warning("Please verify your email first.");
        router.push(`/verify-otp?email=${encodeURIComponent(form.email)}`);
      } else {
        toast.error(getApiError(err));
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-8">
      {/* Header */}
      <div className="mb-7">
        <h1 className="text-2xl font-bold text-slate-800">Sign in</h1>
        <p className="text-slate-500 text-sm mt-1">Access your CA firm portal</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Email */}
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1.5">
            Email address
          </label>
          <div className="relative">
            <Mail size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="email"
              autoComplete="email"
              value={form.email}
              onChange={set("email")}
              placeholder="priya@cafirm.in"
              className={`input-base pl-10 ${errors.email ? "error" : ""}`}
            />
          </div>
          {errors.email && <p className="text-red-500 text-xs mt-1">{errors.email}</p>}
        </div>

        {/* Password */}
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1.5">
            Password
          </label>
          <div className="relative">
            <Lock size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type={showPass ? "text" : "password"}
              autoComplete="current-password"
              value={form.password}
              onChange={set("password")}
              placeholder="••••••••"
              className={`input-base pl-10 pr-10 ${errors.password ? "error" : ""}`}
            />
            <button
              type="button"
              onClick={() => setShowPass((v) => !v)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
            >
              {showPass ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
          </div>
          {errors.password && <p className="text-red-500 text-xs mt-1">{errors.password}</p>}
        </div>

        {/* Submit */}
        <button type="submit" disabled={loading} className="btn-primary w-full mt-2">
          {loading ? (
            <><Loader2 size={16} className="animate-spin" /> Signing in...</>
          ) : (
            <>Sign in <ArrowRight size={16} /></>
          )}
        </button>
      </form>

      {/* Divider */}
      <div className="flex items-center gap-3 my-6">
        <div className="flex-1 h-px bg-slate-200" />
        <span className="text-slate-400 text-xs">or</span>
        <div className="flex-1 h-px bg-slate-200" />
      </div>

      {/* Client login link */}
      <p className="text-center text-sm text-slate-500">
        Are you a business owner?{" "}
        <Link href="/client-login" className="text-blue-700 font-semibold hover:underline">
          Client Login
        </Link>
      </p>

      {/* Register link */}
      <p className="text-center text-sm text-slate-500 mt-6">
        New to BharatCompliance?{" "}
        <Link href="/register" className="text-blue-700 font-semibold hover:underline">
          Create CA account
        </Link>
      </p>
    </div>
  );
}
