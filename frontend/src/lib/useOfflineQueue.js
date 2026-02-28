"use client";

/**
 * useOfflineQueue — React hook for the offline transaction queue.
 *
 * Returns:
 *   count      — number of queued transactions
 *   draining   — true while drain is running
 *   drain()    — manually trigger drain (also runs auto on 'online' event)
 *
 * The hook auto-drains when the browser fires the 'online' event.
 */

import { useState, useEffect, useCallback, useRef } from "react";
import { toast } from "sonner";
import {
  getQueue, removeFromQueue, getQueueCount, dataUrlToFile,
} from "./offlineQueue";
import { transactionsApi } from "./api/transactions";

export function useOfflineQueue() {
  const [count,    setCount]    = useState(0);
  const [draining, setDraining] = useState(false);
  const drainingRef = useRef(false);

  // Sync count from localStorage
  const refreshCount = useCallback(() => {
    setCount(getQueueCount());
  }, []);

  useEffect(() => {
    refreshCount();
  }, [refreshCount]);

  const drain = useCallback(async () => {
    if (drainingRef.current) return;
    const queue = getQueue();
    if (!queue.length) return;
    if (!navigator.onLine) return;

    drainingRef.current = true;
    setDraining(true);

    let succeeded = 0;
    let failed    = 0;

    for (const item of queue) {
      try {
        const file = item.fileDataUrl
          ? dataUrlToFile(item.fileDataUrl)
          : null;

        await (file
          ? transactionsApi.create(item.payload, file)
          : transactionsApi.create(item.payload)
        );

        removeFromQueue(item.id);
        succeeded++;
      } catch {
        failed++;
      }
    }

    drainingRef.current = false;
    setDraining(false);
    refreshCount();

    if (succeeded > 0) {
      toast.success(
        `${succeeded} offline ${succeeded === 1 ? "entry" : "entries"} synced successfully.`,
        { duration: 5000 }
      );
    }
    if (failed > 0) {
      toast.error(`${failed} offline ${failed === 1 ? "entry" : "entries"} failed to sync. Will retry next time.`);
    }
  }, [refreshCount]);

  // Auto-drain on reconnect
  useEffect(() => {
    const handler = () => {
      refreshCount();
      setTimeout(drain, 1500); // small delay to let connection stabilise
    };

    window.addEventListener("online",  handler);
    window.addEventListener("storage", refreshCount); // sync across tabs

    return () => {
      window.removeEventListener("online",  handler);
      window.removeEventListener("storage", refreshCount);
    };
  }, [drain, refreshCount]);

  return { count, draining, drain, refreshCount };
}
