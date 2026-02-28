/**
 * Firebase / FCM initialisation.
 *
 * Config is supplied via NEXT_PUBLIC_* env vars in .env.local:
 *   NEXT_PUBLIC_FIREBASE_API_KEY
 *   NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN
 *   NEXT_PUBLIC_FIREBASE_PROJECT_ID
 *   NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET
 *   NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID
 *   NEXT_PUBLIC_FIREBASE_APP_ID
 *   NEXT_PUBLIC_FIREBASE_VAPID_KEY   ← Firebase Console > Project Settings > Cloud Messaging > Web push certificates
 *
 * If any of the required vars are absent the module no-ops gracefully
 * (dev environments without Firebase configured still work fine).
 */

import { initializeApp, getApps } from "firebase/app";
import { getMessaging, getToken, onMessage } from "firebase/messaging";

// ── Config ────────────────────────────────────────────────────────────

const firebaseConfig = {
  apiKey:            process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
  authDomain:        process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
  projectId:         process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
  storageBucket:     process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID,
  appId:             process.env.NEXT_PUBLIC_FIREBASE_APP_ID,
};

export const isFirebaseConfigured = Boolean(
  firebaseConfig.apiKey && firebaseConfig.projectId
);

// ── Lazy singletons ───────────────────────────────────────────────────

let _app = null;
let _messaging = null;

function _getApp() {
  if (!isFirebaseConfigured || typeof window === "undefined") return null;
  if (_app) return _app;
  _app = getApps().length ? getApps()[0] : initializeApp(firebaseConfig);
  return _app;
}

function _getMessaging() {
  if (_messaging) return _messaging;
  const app = _getApp();
  if (!app) return null;
  try {
    _messaging = getMessaging(app);
    return _messaging;
  } catch {
    // Browser doesn't support messaging (e.g. Safari < 16)
    return null;
  }
}

// ── Public API ────────────────────────────────────────────────────────

/**
 * Request notification permission (prompts the browser permission dialog if
 * `Notification.permission === 'default'`) and return the FCM registration
 * token, or null if unavailable.
 *
 * @param {ServiceWorkerRegistration} swRegistration — our existing sw.js
 * @returns {Promise<string|null>}
 */
export async function requestFcmToken(swRegistration) {
  if (!isFirebaseConfigured) {
    console.log("[FCM] Firebase not configured — skipping.");
    return null;
  }

  const vapidKey = process.env.NEXT_PUBLIC_FIREBASE_VAPID_KEY;
  if (!vapidKey) {
    console.log("[FCM] VAPID key missing — skipping.");
    return null;
  }

  if (!("Notification" in window)) return null;

  const permission = await Notification.requestPermission();
  if (permission !== "granted") {
    console.log("[FCM] Permission:", permission);
    return null;
  }

  const messaging = _getMessaging();
  if (!messaging) return null;

  try {
    const token = await getToken(messaging, {
      vapidKey,
      serviceWorkerRegistration: swRegistration,
    });
    return token || null;
  } catch (err) {
    console.warn("[FCM] getToken failed:", err.message);
    return null;
  }
}

/**
 * Subscribe to foreground push messages (app tab is visible).
 * Returns an unsubscribe function.
 *
 * Usage:
 *   const unsub = subscribeForegroundMessages((payload) => { ... });
 *   return unsub; // cleanup in useEffect
 *
 * @param {(payload: MessagePayload) => void} callback
 * @returns {() => void} unsubscribe
 */
export function subscribeForegroundMessages(callback) {
  const messaging = _getMessaging();
  if (!messaging) return () => {};
  return onMessage(messaging, callback);
}
