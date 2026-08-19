/** Research pilot invite codes passed via URL (?invite=...). */

export const INVITE_QUERY_PARAM = "invite";
const STORAGE_KEY = "ds_research_invite";

export function normalizeInviteCode(value: string | null | undefined): string | null {
  const trimmed = value?.trim();
  return trimmed ? trimmed : null;
}

/** Persist invite from the landing URL for the rest of the browser session. */
export function persistInviteCode(code: string): void {
  if (typeof window === "undefined") return;
  const normalized = normalizeInviteCode(code);
  if (!normalized) return;
  sessionStorage.setItem(STORAGE_KEY, normalized);
}

export function getStoredInviteCode(): string | null {
  if (typeof window === "undefined") return null;
  return normalizeInviteCode(sessionStorage.getItem(STORAGE_KEY));
}

/** Prefer the current URL param; fall back to session storage. */
export function resolveInviteCode(searchParam: string | null): string | null {
  return normalizeInviteCode(searchParam) ?? getStoredInviteCode();
}
