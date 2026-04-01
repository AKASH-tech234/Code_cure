const SESSION_KEY = "epi_session_id";

export function getSessionId(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.sessionStorage.getItem(SESSION_KEY);
}

export function setSessionId(sessionId: string): void {
  if (typeof window === "undefined") {
    return;
  }
  window.sessionStorage.setItem(SESSION_KEY, sessionId);
}

export function clearSessionId(): void {
  if (typeof window === "undefined") {
    return;
  }
  window.sessionStorage.removeItem(SESSION_KEY);
}
