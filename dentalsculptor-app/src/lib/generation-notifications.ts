import { GENERATION_COPY } from "@/lib/generation-copy";

const NOTIFY_PREF_KEY = "ds_notify_on_generation";

export function getNotifyOnGeneration(): boolean {
  if (typeof window === "undefined") return false;
  return localStorage.getItem(NOTIFY_PREF_KEY) === "true";
}

export function setNotifyOnGeneration(enabled: boolean): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(NOTIFY_PREF_KEY, String(enabled));
}

export function isNotificationSupported(): boolean {
  return typeof window !== "undefined" && "Notification" in window;
}

/** Ask for permission when the user opts in — call before starting generation. */
export async function ensureNotificationPermission(): Promise<boolean> {
  if (!isNotificationSupported()) return false;
  if (Notification.permission === "granted") return true;
  if (Notification.permission === "denied") return false;
  const result = await Notification.requestPermission();
  return result === "granted";
}

export function notifyGenerationComplete(body?: string): void {
  if (!isNotificationSupported() || Notification.permission !== "granted") return;
  if (!getNotifyOnGeneration()) return;

  try {
    const notification = new Notification(GENERATION_COPY.notifyReadyTitle, {
      body: body ?? GENERATION_COPY.notifyReadyBody,
      icon: "/icon.png",
      tag: "ds-generation-complete",
    });
    notification.onclick = () => {
      window.focus();
      notification.close();
    };
  } catch {
    // Ignore — e.g. insecure context
  }
}

/** Call when starting generation if notifications are enabled. */
export async function prepareGenerationNotification(): Promise<void> {
  if (getNotifyOnGeneration()) {
    await ensureNotificationPermission();
  }
}
