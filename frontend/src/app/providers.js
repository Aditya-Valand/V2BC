"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster, toast } from "sonner";
import { useState, useEffect } from "react";
import { authApi } from "@/lib/api/auth";

export function Providers({ children }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30 * 1000,
            retry: 1,
            refetchOnWindowFocus: false,
          },
        },
      })
  );

  useEffect(() => {
    if (typeof window === "undefined" || !("serviceWorker" in navigator)) return;

    let swReg = null;

    navigator.serviceWorker
      .register("/sw.js", { scope: "/" })
      .then(async (reg) => {
        swReg = reg;
        console.log("[SW] Registered, scope:", reg.scope);

        // ── Silently refresh FCM token when permission is already granted ──
        if ("Notification" in window && Notification.permission === "granted") {
          try {
            const { requestFcmToken } = await import("@/lib/firebase");
            const token = await requestFcmToken(reg);
            if (token) {
              const cached = localStorage.getItem("bc_fcm_token");
              if (cached !== token) {
                await authApi.registerFcmToken(token).catch(() => {});
                localStorage.setItem("bc_fcm_token", token);
                console.log("[FCM] Token refreshed.");
              }
            }
          } catch {
            // Non-fatal — notifications will still work until token rotates
          }
        }
      })
      .catch((err) => {
        console.warn("[SW] Registration failed:", err);
      });

    // ── Subscribe to foreground push messages ──────────────────────────
    // Shows a toast when the app tab is active and a push arrives.
    let unsubForeground = () => {};
    (async () => {
      try {
        const { subscribeForegroundMessages } = await import("@/lib/firebase");
        unsubForeground = subscribeForegroundMessages((payload) => {
          const title = payload?.notification?.title || "BharatCompliance";
          const body  = payload?.notification?.body  || "You have a new notification.";
          toast.info(`${title}: ${body}`, { duration: 6000 });
        });
      } catch {
        // Firebase not configured — silently skip
      }
    })();

    return () => {
      unsubForeground();
    };
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <Toaster position="top-center" richColors closeButton duration={3500} />
    </QueryClientProvider>
  );
}
