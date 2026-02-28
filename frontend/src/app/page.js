"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import useAuthStore from "@/store/authStore";

/**
 * Root page — redirects based on auth state.
 * CA → /dashboard
 * Client → /home
 * Unauthenticated → /login
 */
export default function RootPage() {
  const router = useRouter();
  const { isAuthenticated, getRole } = useAuthStore();

  useEffect(() => {
    if (!isAuthenticated) {
      router.replace("/login");
      return;
    }
    const role = getRole();
    if (role === "client") {
      router.replace("/home");
    } else {
      router.replace("/dashboard");
    }
  }, [isAuthenticated, getRole, router]);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
    </div>
  );
}
