"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  Users, CheckCircle2, AlertTriangle, CalendarClock,
  TrendingUp, TrendingDown, MoreVertical, Plus,
  Search, SlidersHorizontal, ArrowRight, RefreshCw,
} from "lucide-react";
import { format } from "date-fns";
import { dashboardApi } from "@/lib/api/dashboard";
import { deadlinesApi } from "@/lib/api/deadlines";
import useAuthStore from "@/store/authStore";
import { formatINR, getInitials, timeAgo } from "@/lib/utils";

/* ── Stat card ──────────────────────────────────────────────── */
function StatCard({ label, value, sub, icon: Icon, iconBg, trend }) {
  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-5 flex items-start justify-between">
      <div>
        <p className="text-sm text-slate-500 font-medium">{label}</p>
        <p className="text-3xl font-bold text-slate-800 mt-1">{value}</p>
        {sub && (
          <p className="text-xs text-slate-400 mt-1 flex items-center gap-1">
            {trend === "up"   && <TrendingUp  size={12} className="text-green-500" />}
            {trend === "down" && <TrendingDown size={12} className="text-red-500" />}
            {sub}
          </p>
        )}
      </div>
      <div className={`w-11 h-11 rounded-xl flex items-center justify-center shrink-0 ${iconBg}`}>
        <Icon size={22} />
      </div>
    </div>
  );
}

/* ── Compliance dot ─────────────────────────────────────────── */
const COLOR_MAP = {
  green:  { dot: "bg-green-500", badge: "bg-green-100 text-green-700",  label: "Active" },
  yellow: { dot: "bg-yellow-500", badge: "bg-yellow-100 text-yellow-700", label: "Needs Attention" },
  red:    { dot: "bg-red-500",   badge: "bg-red-100 text-red-700",     label: "Urgent" },
};

function ComplianceBadge({ color }) {
  const c = COLOR_MAP[color] || COLOR_MAP.green;
  return (
    <span className={`inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full ${c.badge}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${c.dot}`} />
      {c.label}
    </span>
  );
}

/* ── Alert severity badge ───────────────────────────────────── */
const SEV_MAP = {
  critical: "bg-red-100 text-red-700 border-red-200",
  high:     "bg-orange-100 text-orange-700 border-orange-200",
  medium:   "bg-yellow-100 text-yellow-700 border-yellow-200",
  low:      "bg-blue-100 text-blue-700 border-blue-200",
};

/* ── Deadline urgency label ─────────────────────────────────── */
function DeadlineUrgency({ dueDate }) {
  const due  = new Date(dueDate);
  const now  = new Date();
  const diff = Math.ceil((due - now) / (1000 * 60 * 60 * 24));
  if (diff < 0)  return <span className="text-xs font-semibold text-red-600 bg-red-50 px-2 py-0.5 rounded-full">Overdue</span>;
  if (diff === 0) return <span className="text-xs font-semibold text-red-600 bg-red-50 px-2 py-0.5 rounded-full">Today</span>;
  if (diff === 1) return <span className="text-xs font-semibold text-orange-600 bg-orange-50 px-2 py-0.5 rounded-full">Tomorrow</span>;
  return <span className="text-xs text-slate-500">{format(due, "MMM d")}</span>;
}

/* ── Skeleton loader ─────────────────────────────────────────── */
function Skeleton({ className = "" }) {
  return <div className={`bg-slate-200 animate-pulse rounded-lg ${className}`} />;
}

/* ── Main page ───────────────────────────────────────────────── */
export default function DashboardPage() {
  const router  = useRouter();
  const { org } = useAuthStore();
  const [search, setSearch]   = useState("");
  const [colorFilter, setColorFilter] = useState("all"); // all | red | yellow | green

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["dashboard"],
    queryFn:  () => dashboardApi.get().then((r) => r.data.data),
    staleTime: 60 * 1000,
  });

  const { data: upcomingData } = useQuery({
    queryKey: ["deadlines-upcoming", 7],
    queryFn:  () => deadlinesApi.upcoming(7).then((r) => r.data.data),
    staleTime: 60 * 1000,
  });

  /* ── Filter + search clients ── */
  const clients = (data?.clients || []).filter((c) => {
    const matchColor  = colorFilter === "all" || c.compliance_color === colorFilter;
    const matchSearch = !search || c.name.toLowerCase().includes(search.toLowerCase());
    return matchColor && matchSearch;
  });

  /* ── Error state ── */
  if (isError) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-4">
        <p className="text-slate-500">Failed to load dashboard data.</p>
        <button onClick={() => refetch()} className="btn-primary">
          <RefreshCw size={15} /> Retry
        </button>
      </div>
    );
  }

  const stats = data?.stats || {};
  const upcomingDeadlines = [
    ...(upcomingData?.overdue   || []),
    ...(upcomingData?.this_week || []),
    ...(upcomingData?.next_week || []),
  ].slice(0, 6);

  return (
    <div className="space-y-6 max-w-[1400px]">

      {/* ── Page header ── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-800">Dashboard</h1>
          <p className="text-sm text-slate-400 mt-0.5">
            {format(new Date(), "EEEE, d MMMM yyyy")}
          </p>
        </div>
        <Link href="/clients/new" className="btn-primary text-sm">
          <Plus size={16} /> Add Client
        </Link>
      </div>

      {/* ── Stat cards ── */}
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
        {isLoading ? (
          Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="bg-white rounded-2xl border border-slate-200 p-5">
              <Skeleton className="h-4 w-24 mb-3" />
              <Skeleton className="h-8 w-16 mb-2" />
              <Skeleton className="h-3 w-32" />
            </div>
          ))
        ) : (
          <>
            <StatCard
              label="Total Clients"
              value={stats.total_clients ?? 0}
              sub={`${stats.invited_not_joined ?? 0} invited, not joined`}
              icon={Users}
              iconBg="bg-blue-100 text-blue-600"
            />
            <StatCard
              label="Active Clients"
              value={stats.active_clients ?? 0}
              sub="Uploaded this month"
              icon={CheckCircle2}
              iconBg="bg-green-100 text-green-600"
              trend="up"
            />
            <StatCard
              label="Attention Needed"
              value={stats.red_clients ?? 0}
              sub={`${stats.yellow_clients ?? 0} more in yellow`}
              icon={AlertTriangle}
              iconBg="bg-red-100 text-red-500"
              trend={stats.red_clients > 0 ? "down" : undefined}
            />
            <StatCard
              label="Upcoming Deadlines"
              value={upcomingData?.summary?.this_week ?? 0}
              sub="Within next 7 days"
              icon={CalendarClock}
              iconBg="bg-purple-100 text-purple-600"
            />
          </>
        )}
      </div>

      {/* ── Main grid: client table + deadlines panel ── */}
      <div className="grid grid-cols-1 xl:grid-cols-[1fr_300px] gap-5">

        {/* Client health table */}
        <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
          {/* Table header */}
          <div className="px-5 py-4 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center gap-3">
            <h2 className="text-base font-semibold text-slate-800 flex-1">Client Health Overview</h2>
            <div className="flex items-center gap-2">
              {/* Search */}
              <div className="relative">
                <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search clients..."
                  className="pl-8 pr-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 w-44"
                />
              </div>
              {/* Color filter */}
              <div className="flex items-center gap-1 border border-slate-200 rounded-lg p-1">
                {["all", "red", "yellow", "green"].map((f) => (
                  <button
                    key={f}
                    onClick={() => setColorFilter(f)}
                    className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors ${
                      colorFilter === f
                        ? "bg-blue-700 text-white"
                        : "text-slate-500 hover:bg-slate-100"
                    }`}
                  >
                    {f === "all" ? "All" : f.charAt(0).toUpperCase() + f.slice(1)}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100">
                  {["CLIENT NAME", "STATUS", "LAST ENTRY", "NEXT DEADLINE", "M. TURNOVER", "ACTIONS"].map((h) => (
                    <th key={h} className="text-left px-5 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wide whitespace-nowrap">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {isLoading ? (
                  Array.from({ length: 5 }).map((_, i) => (
                    <tr key={i} className="border-b border-slate-100">
                      {Array.from({ length: 6 }).map((__, j) => (
                        <td key={j} className="px-5 py-4">
                          <Skeleton className="h-4 w-24" />
                        </td>
                      ))}
                    </tr>
                  ))
                ) : clients.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="text-center py-12 text-slate-400 text-sm">
                      {search ? "No clients match your search." : "No clients yet. Add your first client!"}
                    </td>
                  </tr>
                ) : (
                  clients.map((client) => (
                    <ClientRow key={client.id} client={client} router={router} />
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Footer */}
          {!isLoading && clients.length > 0 && (
            <div className="px-5 py-3 border-t border-slate-100 flex items-center justify-between">
              <p className="text-xs text-slate-400">
                Showing {clients.length} of {data?.clients?.length ?? 0} clients
              </p>
              <Link href="/clients" className="text-xs font-semibold text-blue-700 hover:underline flex items-center gap-1">
                View all <ArrowRight size={12} />
              </Link>
            </div>
          )}
        </div>

        {/* Upcoming deadlines panel */}
        <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between">
            <h2 className="text-base font-semibold text-slate-800">Upcoming Deadlines</h2>
            <Link href="/deadlines" className="text-xs font-semibold text-blue-700 hover:underline">
              View all
            </Link>
          </div>

          <div className="divide-y divide-slate-100">
            {isLoading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="px-5 py-4 flex justify-between">
                  <div className="space-y-1.5">
                    <Skeleton className="h-4 w-28" />
                    <Skeleton className="h-3 w-36" />
                  </div>
                  <Skeleton className="h-5 w-14 rounded-full" />
                </div>
              ))
            ) : upcomingDeadlines.length === 0 ? (
              <p className="text-center py-10 text-slate-400 text-sm">No upcoming deadlines.</p>
            ) : (
              upcomingDeadlines.map((d) => (
                <div key={d.id} className="px-5 py-3.5 flex items-start justify-between gap-3 hover:bg-slate-50 transition-colors">
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-slate-700 truncate">{d.description || d.deadline_type}</p>
                    <p className="text-xs text-slate-400 truncate">
                      {d.client_name || "Unknown client"}
                    </p>
                  </div>
                  <div className="shrink-0">
                    <DeadlineUrgency dueDate={d.due_date} />
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* ── Recent alerts ── */}
      {!isLoading && data?.recent_alerts?.length > 0 && (
        <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between">
            <h2 className="text-base font-semibold text-slate-800">Recent Alerts</h2>
            <Link href="/compliance" className="text-xs font-semibold text-blue-700 hover:underline">
              View all
            </Link>
          </div>
          <div className="divide-y divide-slate-100">
            {data.recent_alerts.map((alert) => (
              <div key={alert.id} className="px-5 py-3.5 flex items-center gap-4">
                <span className={`text-xs font-semibold px-2.5 py-1 rounded-full border ${SEV_MAP[alert.severity] || SEV_MAP.low}`}>
                  {alert.severity}
                </span>
                <p className="text-sm text-slate-700 flex-1">{alert.title}</p>
                <p className="text-xs text-slate-400 shrink-0">{timeAgo(alert.created_at)}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Client table row (extracted for clarity) ───────────────── */
function ClientRow({ client, router }) {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <tr
      className="border-b border-slate-100 hover:bg-slate-50 transition-colors cursor-pointer"
      onClick={() => router.push(`/clients/${client.id}`)}
    >
      {/* Name + type */}
      <td className="px-5 py-4">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center text-xs font-bold text-slate-600 shrink-0">
            {getInitials(client.name)}
          </div>
          <div>
            <p className="font-semibold text-slate-800 text-sm">{client.name}</p>
            <p className="text-xs text-slate-400 capitalize">{client.business_type || "General"}</p>
          </div>
        </div>
      </td>

      {/* Compliance status */}
      <td className="px-5 py-4">
        <ComplianceBadge color={client.compliance_color} />
      </td>

      {/* Last entry */}
      <td className="px-5 py-4 text-sm text-slate-600">
        {client.last_transaction_at
          ? format(new Date(client.last_transaction_at), "MMM d, yyyy")
          : <span className="text-slate-400">No entries</span>}
      </td>

      {/* Next deadline — placeholder from upcoming if available */}
      <td className="px-5 py-4">
        <span className="text-sm text-slate-600">—</span>
      </td>

      {/* Monthly turnover */}
      <td className="px-5 py-4 text-sm font-medium text-slate-700">
        {client.transactions_this_month
          ? `${client.transactions_this_month} txns`
          : <span className="text-slate-400">—</span>}
      </td>

      {/* Actions */}
      <td className="px-5 py-4" onClick={(e) => e.stopPropagation()}>
        <div className="relative">
          <button
            onClick={() => setMenuOpen((v) => !v)}
            className="p-1.5 rounded-lg hover:bg-slate-200 text-slate-400 hover:text-slate-700 transition-colors"
          >
            <MoreVertical size={16} />
          </button>
          {menuOpen && (
            <>
              <div className="fixed inset-0 z-10" onClick={() => setMenuOpen(false)} />
              <div className="absolute right-0 top-8 z-20 bg-white border border-slate-200 rounded-xl shadow-lg py-1.5 w-44">
                {[
                  { label: "View Detail",     path: `/clients/${client.id}`        },
                  { label: "Filing Summary",  path: `/clients/${client.id}/filing`  },
                  { label: "Compliance",      path: `/compliance`                   },
                ].map(({ label, path }) => (
                  <button
                    key={path}
                    onClick={() => { setMenuOpen(false); router.push(path); }}
                    className="w-full text-left px-4 py-2 text-sm text-slate-700 hover:bg-slate-50 transition-colors"
                  >
                    {label}
                  </button>
                ))}
              </div>
            </>
          )}
        </div>
      </td>
    </tr>
  );
}
