"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import type { Session, UserRole } from "@/lib/types";

const STORAGE_KEY = "math-jihc-session";
const SESSION_EVENT = "math-jihc-session-updated";

export function readSession(): Session | null {
  if (typeof window === "undefined") {
    return null;
  }
  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (!raw) {
    return null;
  }
  try {
    return JSON.parse(raw) as Session;
  } catch {
    window.localStorage.removeItem(STORAGE_KEY);
    return null;
  }
}

export function writeSession(session: Session): void {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
  window.dispatchEvent(new Event(SESSION_EVENT));
}

export function clearSession(): void {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.removeItem(STORAGE_KEY);
  window.dispatchEvent(new Event(SESSION_EVENT));
}

export function getDefaultRouteForRole(role: UserRole) {
  return role === "admin" ? "/admin/dashboard" : "/student/dashboard";
}

function subscribe(listener: () => void): () => void {
  const handler = () => listener();
  window.addEventListener("storage", handler);
  window.addEventListener(SESSION_EVENT, handler);
  return () => {
    window.removeEventListener("storage", handler);
    window.removeEventListener(SESSION_EVENT, handler);
  };
}

export function useSession() {
  const [session, setSession] = useState<Session | null>(null);

  useEffect(() => {
    setSession(readSession());
    return subscribe(() => setSession(readSession()));
  }, []);

  return session;
}

export function useProtectedRoute(role: UserRole, redirectTo: string) {
  const router = useRouter();
  const session = useSession();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const current = readSession();
    if (!current || current.user.role !== role) {
      router.replace(redirectTo);
      return;
    }
    setReady(true);
  }, [role, redirectTo, router]);

  return { session, ready };
}

export function useGuestRoute() {
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const current = readSession();
    if (current) {
      router.replace(getDefaultRouteForRole(current.user.role));
      return;
    }
    setReady(true);
  }, [router]);

  return { ready };
}
