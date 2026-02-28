/**
 * Offline transaction queue — localStorage-backed.
 *
 * When the client submits a transaction while offline, we queue it here
 * and drain it automatically when connectivity returns.
 *
 * Each item:
 *   { id, payload, fileDataUrl, createdAt }
 *
 * fileDataUrl: base64 data URL of the attached photo, or null.
 */

const QUEUE_KEY = "bc_offline_tx_queue";

export function getQueue() {
  try {
    return JSON.parse(localStorage.getItem(QUEUE_KEY) || "[]");
  } catch {
    return [];
  }
}

export function getQueueCount() {
  return getQueue().length;
}

export function enqueueTransaction(payload, fileDataUrl = null) {
  const queue = getQueue();
  const item = {
    id:          `otx_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
    payload,
    fileDataUrl,
    createdAt:   new Date().toISOString(),
  };
  queue.push(item);
  localStorage.setItem(QUEUE_KEY, JSON.stringify(queue));
  return item.id;
}

export function removeFromQueue(id) {
  const updated = getQueue().filter((item) => item.id !== id);
  localStorage.setItem(QUEUE_KEY, JSON.stringify(updated));
}

export function clearQueue() {
  localStorage.removeItem(QUEUE_KEY);
}

/**
 * Convert a base64 data URL back to a File object for FormData upload.
 */
export function dataUrlToFile(dataUrl, filename = "photo.jpg") {
  const [header, data] = dataUrl.split(",");
  const mime   = header.match(/:(.*?);/)?.[1] || "image/jpeg";
  const binary = atob(data);
  const arr    = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) arr[i] = binary.charCodeAt(i);
  return new File([arr], filename, { type: mime });
}
