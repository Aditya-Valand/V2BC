"use client";

import { useState, useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import {
  LayoutDashboard, Users, ShieldCheck, CalendarClock,
  Bell, LogOut, Menu, X, ChevronRight, Building2,
  MessageSquare, Settings,
} from "lucide-react";
import useAuthStore from "@/store/authStore";
import { authApi } from "@/lib/api/auth";
import { getApiError } from "@/lib/api/client";
import { getInitials } from "@/lib/utils";

const NAV = [
  { href: "/dashboard",  label: "Dashboard",  icon: LayoutDashboard },
  { href: "/clients",    label: "Clients",     icon: Users },
  { href: "/compliance", label: "Compliance",  icon: ShieldCheck },
  { href: "/deadlines",  label: "Deadlines",   icon: CalendarClock },
  { href: "/reminders",  label: "Reminders",   icon: MessageSquare },
  { href: "/settings",   label: "Settings",    icon: Settings },
];

export default function CALayout({ children }) {
  const router   = useRouter();
  const pathname = usePathname();
  const { user, org, logout, isCA } = useAuthStore();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [loggingOut, setLoggingOut]   = useState(false);

  // Guard: redirect non-CA users
  useEffect(() => {
    if (user && !isCA()) router.replace("/home");
  }, [user, isCA, router]);

  const handleLogout = async () => {
    setLoggingOut(true);
    try {
      const accessToken  = localStorage.getItem("access_token");
      const refreshToken = localStorage.getItem("refresh_token");
      if (accessToken)  await authApi.logout(accessToken).catch(() => {});
      if (refreshToken) await authApi.logout(refreshToken).catch(() => {});
    } catch {
      // ignore — always logout client-side
    } finally {
      logout();
      toast.success("Logged out successfully.");
      router.push("/login");
    }
  };

  const isActive = (href) =>
    href === "/dashboard" ? pathname === "/dashboard" : pathname.startsWith(href);

  const SidebarContent = () => (
    <div className="flex flex-col h-full">
      {/* Logo */}
      <div className="px-5 py-5 border-b border-slate-200">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 bg-blue-700 rounded-lg flex items-center justify-center shrink-0">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
              <path d="M12 2L2 7l10 5 10-5-10-5z" fill="white" />
              <path d="M2 17l10 5 10-5" stroke="white" strokeWidth="2" strokeLinecap="round" />
              <path d="M2 12l10 5 10-5" stroke="white" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </div>
          <div>
            <p className="text-sm font-bold text-slate-800 leading-none">BharatCompliance</p>
            <p className="text-xs text-slate-400 mt-0.5">CA Portal</p>
          </div>
        </div>
      </div>

      {/* Firm badge */}
      {org && (
        <div className="mx-3 mt-3 mb-1 px-3 py-2.5 bg-blue-50 rounded-xl">
          <div className="flex items-center gap-2">
            <Building2 size={14} className="text-blue-600 shrink-0" />
            <div className="min-w-0">
              <p className="text-xs font-semibold text-blue-800 truncate">{org.name}</p>
              <p className="text-xs text-blue-500">{org.city}, {org.state}</p>
            </div>
          </div>
        </div>
      )}

      {/* Nav links */}
      <nav className="flex-1 px-3 py-2 space-y-0.5">
        {NAV.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            onClick={() => setSidebarOpen(false)}
            className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all group
              ${isActive(href)
                ? "bg-blue-700 text-white shadow-sm"
                : "text-slate-600 hover:bg-slate-100 hover:text-slate-800"
              }`}
          >
            <Icon size={18} className={isActive(href) ? "text-white" : "text-slate-400 group-hover:text-slate-600"} />
            {label}
            {isActive(href) && <ChevronRight size={14} className="ml-auto text-blue-200" />}
          </Link>
        ))}
      </nav>

      {/* User profile + logout */}
      <div className="px-3 pb-4 border-t border-slate-200 pt-3 space-y-1">
        <div className="flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-slate-100 cursor-default">
          <div className="w-8 h-8 rounded-full bg-blue-700 flex items-center justify-center text-white text-xs font-bold shrink-0">
            {getInitials(user?.name || "CA")}
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold text-slate-800 truncate">{user?.name}</p>
            <p className="text-xs text-slate-400 truncate">{user?.email}</p>
          </div>
        </div>
        <button
          onClick={handleLogout}
          disabled={loggingOut}
          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-red-600 hover:bg-red-50 transition-colors"
        >
          <LogOut size={17} />
          {loggingOut ? "Signing out..." : "Sign out"}
        </button>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen flex bg-slate-50">
      {/* ── Desktop sidebar ──────────────────────────────────────── */}
      <aside className="hidden lg:flex flex-col w-60 shrink-0 bg-white border-r border-slate-200 fixed top-0 left-0 h-full z-30">
        <SidebarContent />
      </aside>

      {/* ── Mobile sidebar overlay ───────────────────────────────── */}
      {sidebarOpen && (
        <div className="lg:hidden fixed inset-0 z-40 flex">
          <div
            className="absolute inset-0 bg-black/40"
            onClick={() => setSidebarOpen(false)}
          />
          <div className="relative w-64 bg-white h-full shadow-xl z-50">
            <button
              onClick={() => setSidebarOpen(false)}
              className="absolute top-4 right-4 text-slate-500 hover:text-slate-800"
            >
              <X size={20} />
            </button>
            <SidebarContent />
          </div>
        </div>
      )}

      {/* ── Main content area ────────────────────────────────────── */}
      <div className="flex-1 flex flex-col lg:ml-60 min-w-0">
        {/* Top bar */}
        <header className="sticky top-0 z-20 bg-white border-b border-slate-200 px-4 lg:px-6 h-14 flex items-center gap-4">
          {/* Hamburger (mobile) */}
          <button
            onClick={() => setSidebarOpen(true)}
            className="lg:hidden text-slate-500 hover:text-slate-800 p-1"
          >
            <Menu size={22} />
          </button>

          {/* Page breadcrumb */}
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium text-slate-400 uppercase tracking-wide hidden sm:block">
              FIRM PORTAL
            </p>
            <p className="text-sm font-semibold text-slate-700 truncate">
              {org?.name || "CA Portal"}
            </p>
          </div>

          {/* Right actions */}
          <div className="flex items-center gap-2">
            {/* Notifications */}
            <button className="relative p-2 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition-colors">
              <Bell size={19} />
              <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full" />
            </button>

            {/* Avatar */}
            <div className="w-8 h-8 rounded-full bg-blue-700 flex items-center justify-center text-white text-xs font-bold cursor-pointer">
              {getInitials(user?.name || "CA")}
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 p-4 lg:p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
