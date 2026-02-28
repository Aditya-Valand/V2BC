"use client";

/**
 * usePwaInstall — intercepts the browser's `beforeinstallprompt` event.
 *
 * Returns:
 *   canInstall  — true when the banner should be shown
 *   isInstalled — true after successful install or if already standalone
 *   install()   — triggers the native install dialog
 *   dismiss()   — hides banner permanently (localStorage flag)
 */

import { useState, useEffect } from "react";

const DISMISSED_KEY = "bc_pwa_install_dismissed";

export function usePwaInstall() {
  const [deferredPrompt, setDeferred]   = useState(null);
  const [dismissed,      setDismissed]  = useState(false);
  const [isInstalled,    setInstalled]  = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;

    // Already running as installed PWA
    if (window.matchMedia("(display-mode: standalone)").matches ||
        window.navigator.standalone === true) {
      setInstalled(true);
      return;
    }

    // Previously dismissed
    if (localStorage.getItem(DISMISSED_KEY)) {
      setDismissed(true);
      return;
    }

    const handler = (e) => {
      e.preventDefault();
      setDeferred(e);
    };

    window.addEventListener("beforeinstallprompt", handler);
    window.addEventListener("appinstalled", () => {
      setInstalled(true);
      setDeferred(null);
      localStorage.setItem(DISMISSED_KEY, "1");
    });

    return () => window.removeEventListener("beforeinstallprompt", handler);
  }, []);

  const install = async () => {
    if (!deferredPrompt) return false;
    deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    setDeferred(null);
    if (outcome === "accepted") {
      setInstalled(true);
      localStorage.setItem(DISMISSED_KEY, "1");
    }
    return outcome === "accepted";
  };

  const dismiss = () => {
    setDismissed(true);
    localStorage.setItem(DISMISSED_KEY, "1");
  };

  const canInstall = !dismissed && !isInstalled && !!deferredPrompt;

  return { canInstall, isInstalled, install, dismiss };
}
