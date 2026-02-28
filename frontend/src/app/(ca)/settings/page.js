"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import {
  User, Lock, Building2, Phone, Mail, MapPin, Hash,
  CheckCircle2, Eye, EyeOff, Shield, CreditCard, Save,
} from "lucide-react";
import { toast } from "sonner";
import { authApi } from "@/lib/api/auth";
import { getApiError } from "@/lib/api/client";
import { getInitials } from "@/lib/utils";
import useAuthStore from "@/store/authStore";

// ── Section wrapper ──────────────────────────────────────────────────

function Section({ icon: Icon, title, description, children }) {
  return (
    <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
      <div className="px-5 py-4 border-b border-slate-100 flex items-start gap-3">
        <div className="w-9 h-9 rounded-xl bg-blue-100 flex items-center justify-center shrink-0 mt-0.5">
          <Icon size={16} className="text-blue-700" />
        </div>
        <div>
          <h2 className="text-sm font-bold text-slate-800">{title}</h2>
          {description && <p className="text-xs text-slate-400 mt-0.5">{description}</p>}
        </div>
      </div>
      <div className="p-5">{children}</div>
    </div>
  );
}

// ── Input field ──────────────────────────────────────────────────────

function Field({ label, error, children }) {
  return (
    <div>
      <label className="block text-xs font-semibold text-slate-500 mb-1.5">{label}</label>
      {children}
      {error && <p className="text-xs text-red-500 mt-1">{error}</p>}
    </div>
  );
}

// ── Profile section ──────────────────────────────────────────────────

function ProfileSection() {
  const { user, org, setAuth } = useAuthStore();
  const [name,  setName]  = useState(user?.name  || "");
  const [phone, setPhone] = useState(user?.phone || "");
  const [errors, setErrors] = useState({});

  const validate = () => {
    const e = {};
    if (!name.trim() || name.trim().length < 2) e.name = "Name must be at least 2 characters.";
    if (phone && !/^[6-9]\d{9}$/.test(phone.replace(/\s/g, "")))
      e.phone = "Enter a valid 10-digit Indian mobile number.";
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const mutation = useMutation({
    mutationFn: () => authApi.updateProfile({ name: name.trim(), phone: phone.trim() || null }),
    onSuccess: (res) => {
      const updated = res.data.data.user;
      setAuth({ user: { ...user, ...updated }, org });
      toast.success("Profile updated.");
    },
    onError: (err) => toast.error(getApiError(err)),
  });

  const handleSave = () => {
    if (!validate()) return;
    mutation.mutate();
  };

  return (
    <Section icon={User} title="Your Profile" description="Update your name and contact number.">
      <div className="flex items-center gap-4 mb-5">
        <div className="w-16 h-16 rounded-2xl bg-blue-700 flex items-center justify-center text-white text-xl font-bold shrink-0">
          {getInitials(user?.name || "CA")}
        </div>
        <div>
          <p className="text-base font-bold text-slate-800">{user?.name}</p>
          <p className="text-sm text-slate-400">{user?.email}</p>
          <span className="inline-block mt-1 text-xs font-semibold bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full capitalize">
            {user?.role?.replace("_", " ")}
          </span>
        </div>
      </div>

      <div className="space-y-4">
        <Field label="Full Name" error={errors.name}>
          <div className="relative">
            <User size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Your full name"
              className="input-base pl-9"
            />
          </div>
        </Field>

        <Field label="Email Address">
          <div className="relative">
            <Mail size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
            <input
              value={user?.email || ""}
              readOnly
              className="input-base pl-9 bg-slate-50 text-slate-500 cursor-not-allowed"
            />
          </div>
          <p className="text-xs text-slate-400 mt-1">Email cannot be changed.</p>
        </Field>

        <Field label="Mobile Number" error={errors.phone}>
          <div className="relative">
            <Phone size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
            <input
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="10-digit mobile number"
              maxLength={10}
              className="input-base pl-9"
            />
          </div>
        </Field>

        <button
          onClick={handleSave}
          disabled={mutation.isPending}
          className="btn-primary flex items-center gap-2"
        >
          {mutation.isPending ? (
            <span className="flex items-center gap-2"><Save size={15} className="animate-pulse" /> Saving…</span>
          ) : (
            <><Save size={15} /> Save Profile</>
          )}
        </button>
      </div>
    </Section>
  );
}

// ── Change Password section ──────────────────────────────────────────

function PasswordSection() {
  const [current,  setCurrent]  = useState("");
  const [newPwd,   setNewPwd]   = useState("");
  const [confirm,  setConfirm]  = useState("");
  const [showCur,  setShowCur]  = useState(false);
  const [showNew,  setShowNew]  = useState(false);
  const [errors,   setErrors]   = useState({});

  const validate = () => {
    const e = {};
    if (!current) e.current = "Enter your current password.";
    if (!newPwd)  e.newPwd = "Enter a new password.";
    else if (newPwd.length < 8) e.newPwd = "At least 8 characters required.";
    else if (!/\d/.test(newPwd)) e.newPwd = "Must contain at least one number.";
    if (newPwd !== confirm) e.confirm = "Passwords do not match.";
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const mutation = useMutation({
    mutationFn: () => authApi.changePassword(current, newPwd),
    onSuccess: () => {
      toast.success("Password changed successfully.");
      setCurrent(""); setNewPwd(""); setConfirm(""); setErrors({});
    },
    onError: (err) => toast.error(getApiError(err)),
  });

  const handleChange = () => {
    if (!validate()) return;
    mutation.mutate();
  };

  const PwdInput = ({ label, value, onChange, show, setShow, error, placeholder }) => (
    <Field label={label} error={error}>
      <div className="relative">
        <Lock size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
        <input
          type={show ? "text" : "password"}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className="input-base pl-9 pr-10"
        />
        <button
          type="button"
          onClick={() => setShow(!show)}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
        >
          {show ? <EyeOff size={15} /> : <Eye size={15} />}
        </button>
      </div>
    </Field>
  );

  return (
    <Section icon={Lock} title="Change Password" description="Use a strong password with at least 8 characters and one number.">
      <div className="space-y-4">
        <PwdInput
          label="Current Password"
          value={current}
          onChange={setCurrent}
          show={showCur}
          setShow={setShowCur}
          error={errors.current}
          placeholder="Your current password"
        />
        <PwdInput
          label="New Password"
          value={newPwd}
          onChange={setNewPwd}
          show={showNew}
          setShow={setShowNew}
          error={errors.newPwd}
          placeholder="Min 8 chars, include a number"
        />
        <Field label="Confirm New Password" error={errors.confirm}>
          <div className="relative">
            <Lock size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
            <input
              type="password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              placeholder="Repeat new password"
              className={`input-base pl-9 ${confirm && newPwd === confirm ? "border-green-400" : ""}`}
            />
            {confirm && newPwd === confirm && (
              <CheckCircle2 size={15} className="absolute right-3 top-1/2 -translate-y-1/2 text-green-500" />
            )}
          </div>
        </Field>

        {/* Strength indicator */}
        {newPwd.length > 0 && (
          <div>
            <div className="flex gap-1 mb-1">
              {[1, 2, 3, 4].map((level) => {
                const strength = Math.min(
                  4,
                  (newPwd.length >= 8 ? 1 : 0) +
                  (/\d/.test(newPwd) ? 1 : 0) +
                  (/[A-Z]/.test(newPwd) ? 1 : 0) +
                  (/[^A-Za-z0-9]/.test(newPwd) ? 1 : 0)
                );
                const colors = ["bg-red-400", "bg-orange-400", "bg-yellow-400", "bg-green-500"];
                return (
                  <div
                    key={level}
                    className={`flex-1 h-1.5 rounded-full transition-all ${
                      level <= strength ? colors[strength - 1] : "bg-slate-200"
                    }`}
                  />
                );
              })}
            </div>
            <p className="text-xs text-slate-400">
              {(() => {
                const s =
                  (newPwd.length >= 8 ? 1 : 0) +
                  (/\d/.test(newPwd) ? 1 : 0) +
                  (/[A-Z]/.test(newPwd) ? 1 : 0) +
                  (/[^A-Za-z0-9]/.test(newPwd) ? 1 : 0);
                return ["Weak", "Fair", "Good", "Strong"][Math.min(s - 1, 3)] || "Weak";
              })()} password
            </p>
          </div>
        )}

        <button
          onClick={handleChange}
          disabled={mutation.isPending}
          className="btn-primary flex items-center gap-2"
        >
          {mutation.isPending ? (
            <><Shield size={15} className="animate-pulse" /> Updating…</>
          ) : (
            <><Shield size={15} /> Update Password</>
          )}
        </button>
      </div>
    </Section>
  );
}

// ── Firm details section ─────────────────────────────────────────────

function FirmSection() {
  const { org } = useAuthStore();

  const fields = [
    { icon: Building2, label: "Firm Name",      value: org?.name },
    { icon: MapPin,    label: "City",            value: org?.city },
    { icon: MapPin,    label: "State",           value: org?.state },
    { icon: CreditCard, label: "Plan",           value: org?.plan?.toUpperCase() || "FREE" },
    { icon: Hash,      label: "Total Clients",   value: org?.client_count ?? "—" },
  ];

  return (
    <Section icon={Building2} title="Firm Details" description="Your registered CA firm information.">
      <div className="space-y-3">
        {fields.map(({ icon: Icon, label, value }) => (
          <div key={label} className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center shrink-0">
              <Icon size={13} className="text-slate-500" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs text-slate-400">{label}</p>
              <p className="text-sm font-semibold text-slate-700">{value || "—"}</p>
            </div>
          </div>
        ))}
      </div>
      <p className="text-xs text-slate-400 mt-4 pt-4 border-t border-slate-100">
        To update firm details, please contact support.
      </p>
    </Section>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────

export default function SettingsPage() {
  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-slate-800">Settings</h1>
        <p className="text-sm text-slate-400 mt-0.5">Manage your profile, password, and firm information.</p>
      </div>

      <ProfileSection />
      <PasswordSection />
      <FirmSection />
    </div>
  );
}
