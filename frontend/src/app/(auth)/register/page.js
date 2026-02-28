"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import {
  User, Mail, Lock, Phone, Building2, MapPin, Eye, EyeOff,
  ArrowRight, ArrowLeft, Loader2, CheckCircle2,
} from "lucide-react";
import { authApi } from "@/lib/api/auth";
import { getApiError } from "@/lib/api/client";

/* ── Validation helpers ──────────────────────────────────────── */
const validators = {
  name:        (v) => v.trim().length >= 2 ? null : "Name must be at least 2 characters",
  email:       (v) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v) ? null : "Enter a valid email",
  password:    (v) => {
    if (v.length < 8) return "Password must be at least 8 characters";
    if (!/\d/.test(v)) return "Must include at least one number";
    return null;
  },
  firm_name:   (v) => v.trim().length >= 2 ? null : "Firm name must be at least 2 characters",
  city:        (v) => v.trim().length >= 2 ? null : "City is required",
  state:       (v) => v.trim().length >= 2 ? null : "State is required",
  phone:       (v) => !v || /^[6-9]\d{9}$/.test(v) ? null : "Enter valid 10-digit mobile number",
};

const STEPS = [
  { id: 1, label: "Your details",  fields: ["name", "email", "phone"] },
  { id: 2, label: "Set password",  fields: ["password"] },
  { id: 3, label: "Firm details",  fields: ["firm_name", "city", "state"] },
];

export default function RegisterPage() {
  const router = useRouter();

  const [step, setStep] = useState(1);
  const [form, setForm] = useState({
    name: "", email: "", phone: "",
    password: "", showPass: false,
    firm_name: "", city: "", state: "", license_number: "",
  });
  const [errors, setErrors]   = useState({});
  const [loading, setLoading] = useState(false);

  const set = (field) => (e) => {
    setForm((f) => ({ ...f, [field]: e.target.value }));
    if (errors[field]) setErrors((er) => ({ ...er, [field]: null }));
  };

  const validateStep = () => {
    const currentFields = STEPS[step - 1].fields;
    const newErrors = {};
    currentFields.forEach((f) => {
      if (validators[f]) {
        const err = validators[f](form[f] || "");
        if (err) newErrors[f] = err;
      }
    });
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const nextStep = () => {
    if (validateStep()) setStep((s) => s + 1);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validateStep()) return;

    setLoading(true);
    try {
      const payload = {
        name:      form.name.trim(),
        email:     form.email.trim().toLowerCase(),
        password:  form.password,
        firm_name: form.firm_name.trim(),
        city:      form.city.trim(),
        state:     form.state.trim(),
        ...(form.phone           && { phone:          form.phone }),
        ...(form.license_number  && { license_number: form.license_number }),
      };

      const res = await authApi.register(payload);
      const { user_id, otp_dev_only } = res.data.data;

      toast.success("Account created! Check your email for the OTP.");
      if (otp_dev_only) {
        toast.info(`DEV OTP: ${otp_dev_only}`, { duration: 20000 });
      }
      router.push(`/verify-otp?user_id=${user_id}`);
    } catch (err) {
      const status = err.response?.status;
      if (status === 409) {
        toast.error("Email or phone already registered. Please log in.");
        router.push("/login");
      } else {
        toast.error(getApiError(err));
      }
    } finally {
      setLoading(false);
    }
  };

  /* ── Step indicator ── */
  const StepIndicator = () => (
    <div className="flex items-center justify-between mb-7">
      {STEPS.map((s, i) => (
        <div key={s.id} className="flex items-center flex-1">
          <div className="flex flex-col items-center">
            <div
              className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold transition-all ${
                step > s.id
                  ? "bg-green-500 text-white"
                  : step === s.id
                  ? "bg-blue-700 text-white"
                  : "bg-slate-200 text-slate-400"
              }`}
            >
              {step > s.id ? <CheckCircle2 size={16} /> : s.id}
            </div>
            <span className={`text-xs mt-1 font-medium ${step === s.id ? "text-blue-700" : "text-slate-400"}`}>
              {s.label}
            </span>
          </div>
          {i < STEPS.length - 1 && (
            <div className={`flex-1 h-0.5 mx-2 mb-4 ${step > s.id ? "bg-green-400" : "bg-slate-200"}`} />
          )}
        </div>
      ))}
    </div>
  );

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-800">Create account</h1>
        <p className="text-slate-500 text-sm mt-1">Join as a CA firm — free to start</p>
      </div>

      <StepIndicator />

      {/* ── STEP 1: Personal details ── */}
      {step === 1 && (
        <div className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">Full Name</label>
            <div className="relative">
              <User size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
              <input value={form.name} onChange={set("name")} placeholder="Priya Nair"
                className={`input-base pl-10 ${errors.name ? "error" : ""}`} />
            </div>
            {errors.name && <p className="text-red-500 text-xs mt-1">{errors.name}</p>}
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">Email address</label>
            <div className="relative">
              <Mail size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
              <input type="email" value={form.email} onChange={set("email")} placeholder="priya@cafirm.in"
                className={`input-base pl-10 ${errors.email ? "error" : ""}`} />
            </div>
            {errors.email && <p className="text-red-500 text-xs mt-1">{errors.email}</p>}
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">
              Phone <span className="text-slate-400 font-normal">(optional)</span>
            </label>
            <div className="relative">
              <div className="absolute left-3.5 top-1/2 -translate-y-1/2 flex items-center gap-1.5">
                <Phone size={14} className="text-slate-400" />
                <span className="text-slate-500 text-sm font-medium">+91</span>
              </div>
              <input value={form.phone} onChange={set("phone")} placeholder="9876543210"
                className={`input-base pl-14 ${errors.phone ? "error" : ""}`} />
            </div>
            {errors.phone && <p className="text-red-500 text-xs mt-1">{errors.phone}</p>}
          </div>

          <button type="button" onClick={nextStep} className="btn-primary w-full">
            Continue <ArrowRight size={16} />
          </button>
        </div>
      )}

      {/* ── STEP 2: Password ── */}
      {step === 2 && (
        <div className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">Create Password</label>
            <div className="relative">
              <Lock size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type={form.showPass ? "text" : "password"}
                value={form.password}
                onChange={set("password")}
                placeholder="Min 8 characters, at least 1 number"
                className={`input-base pl-10 pr-10 ${errors.password ? "error" : ""}`}
              />
              <button type="button" onClick={() => setForm((f) => ({ ...f, showPass: !f.showPass }))}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600">
                {form.showPass ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
            {errors.password && <p className="text-red-500 text-xs mt-1">{errors.password}</p>}

            {/* Password strength indicators */}
            <div className="mt-2 flex gap-1.5">
              {[
                form.password.length >= 8,
                /[A-Z]/.test(form.password),
                /\d/.test(form.password),
                form.password.length >= 12,
              ].map((ok, i) => (
                <div key={i} className={`flex-1 h-1 rounded-full transition-colors ${ok ? "bg-green-500" : "bg-slate-200"}`} />
              ))}
            </div>
            <p className="text-xs text-slate-400 mt-1.5">
              {form.password.length === 0 ? "Use 8+ characters with at least 1 number" :
               form.password.length < 8 ? "Too short" :
               !/\d/.test(form.password) ? "Add a number" : "Good password ✓"}
            </p>
          </div>

          <div className="flex gap-3">
            <button type="button" onClick={() => setStep(1)} className="btn-outline flex-1">
              <ArrowLeft size={16} /> Back
            </button>
            <button type="button" onClick={nextStep} className="btn-primary flex-1">
              Continue <ArrowRight size={16} />
            </button>
          </div>
        </div>
      )}

      {/* ── STEP 3: Firm details ── */}
      {step === 3 && (
        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">CA Firm Name</label>
            <div className="relative">
              <Building2 size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
              <input value={form.firm_name} onChange={set("firm_name")} placeholder="Nair & Associates"
                className={`input-base pl-10 ${errors.firm_name ? "error" : ""}`} />
            </div>
            {errors.firm_name && <p className="text-red-500 text-xs mt-1">{errors.firm_name}</p>}
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">City</label>
              <div className="relative">
                <MapPin size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
                <input value={form.city} onChange={set("city")} placeholder="Kochi"
                  className={`input-base pl-9 ${errors.city ? "error" : ""}`} />
              </div>
              {errors.city && <p className="text-red-500 text-xs mt-1">{errors.city}</p>}
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">State</label>
              <input value={form.state} onChange={set("state")} placeholder="Kerala"
                className={`input-base ${errors.state ? "error" : ""}`} />
              {errors.state && <p className="text-red-500 text-xs mt-1">{errors.state}</p>}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">
              License Number <span className="text-slate-400 font-normal">(optional)</span>
            </label>
            <input value={form.license_number} onChange={set("license_number")}
              placeholder="MRN12345"
              className="input-base" />
          </div>

          <div className="flex gap-3">
            <button type="button" onClick={() => setStep(2)} className="btn-outline flex-1">
              <ArrowLeft size={16} /> Back
            </button>
            <button type="submit" disabled={loading} className="btn-primary flex-1">
              {loading ? <><Loader2 size={16} className="animate-spin" /> Creating...</> : <>Create account <ArrowRight size={16} /></>}
            </button>
          </div>
        </form>
      )}

      {/* Login link */}
      <p className="text-center text-sm text-slate-500 mt-6">
        Already have an account?{" "}
        <Link href="/login" className="text-blue-700 font-semibold hover:underline">
          Sign in
        </Link>
      </p>
    </div>
  );
}
