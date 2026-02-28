"use client";

import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import {
  Home, PlusCircle, Receipt, CalendarClock, LogOut, Image,
} from "lucide-react";
import useAuthStore from "@/store/authStore";
import { authApi } from "@/lib/api/auth";
import { getInitials } from "@/lib/utils";

const NAV = [
  { href: "/home",             label: "Home",      icon: Home          },
  { href: "/transactions/new", label: "Add Entry", icon: PlusCircle    },
  { href: "/transactions",     label: "History",   icon: Receipt       },
  { href: "/evidence",         label: "Receipts",  icon: Image         },
  { href: "/my-deadlines",     label: "Deadlines", icon: CalendarClock },
];

export default function ClientLayout({ children }) {
  const router   = useRouter();
  const pathname = usePathname();
  const { user, org, logout, isClient } = useAuthStore();

  // Guard: only clients
  useEffect(() => {
    if (user && !isClient()) router.replace("/dashboard");
  }, [user, isClient, router]);

  const handleLogout = async () => {
    try {
      const at = localStorage.getItem("access_token");
      const rt = localStorage.getItem("refresh_token");
      if (at) await authApi.logout(at).catch(() => {});
      if (rt) await authApi.logout(rt).catch(() => {});
    } finally {
      logout();
      toast.success("Logged out.");
      router.push("/login");
    }
  };

  const isActive = (href) => {
    if (href === "/home") return pathname === "/home";
    if (href === "/transactions") return pathname === "/transactions";
    if (href === "/evidence") return pathname === "/evidence";
    return pathname.startsWith(href);
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 max-w-md mx-auto relative">

      {/* ── Top header ── */}
      <header className="sticky top-0 z-20 bg-white border-b border-slate-200 px-4 py-3 flex items-center justify-between">
        {/* Logo + business name */}
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="w-8 h-8 bg-blue-700 rounded-lg flex items-center justify-center shrink-0">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
              <path d="M12 2L2 7l10 5 10-5-10-5z" fill="white" />
              <path d="M2 17l10 5 10-5" stroke="white" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </div>
          <div className="min-w-0">
            <p className="text-xs font-bold text-slate-800 truncate leading-none">
              BharatCompliance
            </p>
            {org && (
              <p className="text-xs text-slate-400 truncate mt-0.5">{org.name}</p>
            )}
          </div>
        </div>

        {/* Right: user avatar + logout */}
        <div className="flex items-center gap-2">
          <div className="text-right hidden xs:block">
            <p className="text-xs font-semibold text-slate-700 leading-none">{user?.name}</p>
            <p className="text-xs text-slate-400 mt-0.5">Client</p>
          </div>
          <button
            onClick={handleLogout}
            title="Sign out"
            className="w-9 h-9 rounded-full bg-slate-100 hover:bg-red-50 flex items-center justify-center text-slate-500 hover:text-red-600 transition-colors"
          >
            <LogOut size={16} />
          </button>
        </div>
      </header>

      {/* ── Page content ── */}
      <main className="flex-1 pb-20 overflow-y-auto">
        {children}
      </main>

      {/* ── Bottom navigation ── */}
      <nav className="fixed bottom-0 left-1/2 -translate-x-1/2 w-full max-w-md z-20 bg-white border-t border-slate-200 px-2 py-1 safe-area-bottom">
        <div className="flex items-center justify-around">
          {NAV.map(({ href, label, icon: Icon }) => {
            const active = isActive(href);
            const isAdd  = href === "/transactions/new";
            return (
              <Link
                key={href}
                href={href}
                className={`flex flex-col items-center gap-0.5 px-1.5 py-2 rounded-xl transition-all min-w-0 flex-1
                  ${isAdd
                    ? "relative"
                    : active
                    ? "text-blue-700"
                    : "text-slate-400 hover:text-slate-600"
                  }`}
              >
                {isAdd ? (
                  /* ── Add Entry FAB-style ── */
                  <div className="absolute -top-5 left-1/2 -translate-x-1/2 w-12 h-12 bg-blue-700 rounded-full shadow-lg flex items-center justify-center">
                    <Icon size={20} color="white" />
                  </div>
                ) : (
                  <Icon
                    size={20}
                    className={active ? "text-blue-700" : "text-slate-400"}
                    strokeWidth={active ? 2.5 : 1.8}
                  />
                )}

                {isAdd ? (
                  <span className="mt-7 text-[9px] font-semibold text-blue-700">Add</span>
                ) : (
                  <span className={`text-[9px] font-medium truncate ${active ? "text-blue-700" : "text-slate-400"}`}>
                    {label}
                  </span>
                )}

                {/* Active indicator */}
                {!isAdd && active && (
                  <span className="absolute bottom-1 w-1 h-1 bg-blue-700 rounded-full" />
                )}
              </Link>
            );
          })}
        </div>
      </nav>
    </div>
  );
}
