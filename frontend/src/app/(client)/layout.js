"use client";

import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import {
  Home, PlusCircle, Receipt, CalendarClock, Image, UserCircle,
} from "lucide-react";
import useAuthStore from "@/store/authStore";
import { authApi } from "@/lib/api/auth";
import { getInitials } from "@/lib/utils";
import { useOfflineQueue } from "@/lib/useOfflineQueue";

const NAV = [
  { href: "/home",             label: "Home",      icon: Home          },
  { href: "/transactions/new", label: "Add",       icon: PlusCircle    },
  { href: "/transactions",     label: "History",   icon: Receipt       },
  { href: "/evidence",         label: "Receipts",  icon: Image         },
  { href: "/my-deadlines",     label: "Deadlines", icon: CalendarClock },
];

export default function ClientLayout({ children }) {
  const router   = useRouter();
  const pathname = usePathname();
  const { user, org, logout, isClient } = useAuthStore();
  const { count: offlineCount, draining } = useOfflineQueue();

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
    if (href === "/home")         return pathname === "/home";
    if (href === "/transactions") return pathname === "/transactions";
    if (href === "/evidence")     return pathname === "/evidence";
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

        {/* Right: offline badge + profile avatar */}
        <div className="flex items-center gap-2">
          {/* Offline sync indicator */}
          {offlineCount > 0 && (
            <div
              title={draining ? "Syncing offline entries…" : `${offlineCount} entry pending sync`}
              className={`flex items-center gap-1 text-xs font-semibold px-2 py-1 rounded-full
                ${draining
                  ? "bg-blue-100 text-blue-700 animate-pulse"
                  : "bg-orange-100 text-orange-700"
                }`}
            >
              <span className="w-1.5 h-1.5 rounded-full bg-current" />
              {draining ? "Syncing…" : `${offlineCount} offline`}
            </div>
          )}

          {/* Profile avatar (tappable) */}
          <Link
            href="/profile"
            title="My profile"
            className="w-9 h-9 rounded-full bg-blue-700 flex items-center justify-center text-white text-xs font-bold hover:bg-blue-800 transition-colors shrink-0"
          >
            {getInitials(user?.name || "?")}
          </Link>
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
                  /* FAB-style Add button with offline badge */
                  <div className="absolute -top-5 left-1/2 -translate-x-1/2">
                    <div className="w-12 h-12 bg-blue-700 rounded-full shadow-lg flex items-center justify-center">
                      <Icon size={20} color="white" />
                    </div>
                    {offlineCount > 0 && (
                      <span className="absolute -top-1 -right-1 w-4 h-4 bg-orange-500 text-white text-[9px] font-bold rounded-full flex items-center justify-center">
                        {offlineCount > 9 ? "9+" : offlineCount}
                      </span>
                    )}
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

                {/* Active dot */}
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
