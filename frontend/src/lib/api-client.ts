"use client";

import { clearSession, readSession } from "@/lib/session";
import type {
  AdminDashboardPayload,
  Session,
  StudentDashboardPayload,
  StudentTestPayload,
  SubmissionResponse,
  TaskListPayload
} from "@/lib/types";

type CacheEntry = {
  expiresAt: number;
  payload: unknown;
};

type RequestOptions = {
  method?: string;
  cacheTtlMs?: number;
  auth?: boolean;
  json?: unknown;
  body?: BodyInit | null;
  headers?: HeadersInit;
  invalidatePrefixes?: string[];
};

const DEFAULT_TTL = 20_000;
const responseCache = new Map<string, CacheEntry>();
const inFlight = new Map<string, Promise<unknown>>();
const CACHE_SCOPE = {
  studentDashboard: "/api/v1/student/dashboard",
  studentTests: "/api/v1/student/tests/",
  adminDashboard: "/api/v1/admin/dashboard",
  adminTasks: "/api/v1/admin/tasks"
} as const;

function buildCacheKey(
  path: string,
  method: string,
  session: Session | null,
  bodyKey: string
) {
  return `${method}:${path}:${session?.user.id ?? "anon"}:${bodyKey}`;
}

function getBodyKey(json: unknown, body: BodyInit | null | undefined) {
  if (json !== undefined) {
    return JSON.stringify(json);
  }
  if (typeof body === "string") {
    return body;
  }
  return "";
}

export function invalidateCache(...prefixes: string[]) {
  if (!prefixes.length) {
    responseCache.clear();
    return;
  }
  for (const key of responseCache.keys()) {
    if (prefixes.some((prefix) => key.includes(prefix))) {
      responseCache.delete(key);
    }
  }
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const method = options.method ?? "GET";
  const session = options.auth === false ? null : readSession();
  const cacheable = method === "GET";
  const body = options.json !== undefined ? JSON.stringify(options.json) : options.body;
  const cacheKey = buildCacheKey(path, method, session, getBodyKey(options.json, body));

  if (cacheable) {
    const cached = responseCache.get(cacheKey);
    if (cached && cached.expiresAt > Date.now()) {
      return cached.payload as T;
    }
    const existing = inFlight.get(cacheKey);
    if (existing) {
      return existing as Promise<T>;
    }
  }

  const headers = new Headers(options.headers);
  if (session?.token) {
    headers.set("Authorization", `Bearer ${session.token}`);
  }
  if (options.json !== undefined) {
    headers.set("Content-Type", "application/json");
  }

  const fetchPromise = fetch(path, {
    method,
    headers,
    body,
    cache: "no-store"
  })
    .then(async (response) => {
      const contentType = response.headers.get("content-type") ?? "";
      const payload = contentType.includes("application/json")
        ? ((await response.json()) as unknown)
        : await response.text();

      if (response.status === 401) {
        clearSession();
      }
      if (!response.ok) {
        const message =
          typeof payload === "object" && payload && "detail" in payload
            ? String((payload as { detail: string }).detail)
            : "Request failed";
        throw new Error(message);
      }
      if (cacheable) {
        responseCache.set(cacheKey, {
          expiresAt: Date.now() + (options.cacheTtlMs ?? DEFAULT_TTL),
          payload
        });
      }
      if (options.invalidatePrefixes?.length) {
        invalidateCache(...options.invalidatePrefixes);
      }
      return payload as T;
    })
    .finally(() => {
      inFlight.delete(cacheKey);
    });

  if (cacheable) {
    inFlight.set(cacheKey, fetchPromise);
  }

  return fetchPromise;
}

export const apiClient = {
  login(email: string, password: string, role: "student" | "admin") {
    return request<{ token: string; user: Session["user"] }>("/api/v1/auth/login", {
      method: "POST",
      auth: false,
      json: { email, password, role }
    });
  },
  getStudentDashboard() {
    return request<StudentDashboardPayload>("/api/v1/student/dashboard", {
      cacheTtlMs: 30_000
    });
  },
  getStudentTest(taskId: number | string) {
    return request<StudentTestPayload>(`/api/v1/student/tests/${taskId}`, {
      cacheTtlMs: 15_000
    });
  },
  submitStudentTest(taskId: number | string, answer: string) {
    return request<SubmissionResponse>(`/api/v1/student/tests/${taskId}/submit`, {
      method: "POST",
      json: { answer },
      invalidatePrefixes: [
        CACHE_SCOPE.studentDashboard,
        CACHE_SCOPE.studentTests,
        CACHE_SCOPE.adminDashboard
      ]
    });
  },
  getAdminDashboard() {
    return request<AdminDashboardPayload>("/api/v1/admin/dashboard", {
      cacheTtlMs: 20_000
    });
  },
  getAdminTasks(search = "") {
    const query = search ? `?search=${encodeURIComponent(search)}` : "";
    return request<TaskListPayload>(`/api/v1/admin/tasks${query}`, {
      cacheTtlMs: 10_000
    });
  },
  createTask(formData: FormData) {
    return request<{ item: TaskListPayload["items"][number] }>("/api/v1/admin/tasks", {
      method: "POST",
      body: formData,
      invalidatePrefixes: [
        CACHE_SCOPE.adminTasks,
        CACHE_SCOPE.studentDashboard,
        CACHE_SCOPE.adminDashboard,
        CACHE_SCOPE.studentTests
      ]
    });
  },
  importTasksJson(formData: FormData) {
    return request<{ count: number; items: TaskListPayload["items"] }>(
      "/api/v1/admin/tasks/import-json",
      {
        method: "POST",
        body: formData,
        invalidatePrefixes: [
          CACHE_SCOPE.adminTasks,
          CACHE_SCOPE.studentDashboard,
          CACHE_SCOPE.adminDashboard,
          CACHE_SCOPE.studentTests
        ]
      }
    );
  },
  updateTask(taskId: number, formData: FormData) {
    return request<{ item: TaskListPayload["items"][number] }>(`/api/v1/admin/tasks/${taskId}`, {
      method: "PUT",
      body: formData,
      invalidatePrefixes: [
        CACHE_SCOPE.adminTasks,
        CACHE_SCOPE.studentDashboard,
        CACHE_SCOPE.adminDashboard,
        CACHE_SCOPE.studentTests
      ]
    });
  },
  deleteTask(taskId: number) {
    return request<{ ok: boolean }>(`/api/v1/admin/tasks/${taskId}`, {
      method: "DELETE",
      invalidatePrefixes: [
        CACHE_SCOPE.adminTasks,
        CACHE_SCOPE.studentDashboard,
        CACHE_SCOPE.adminDashboard,
        CACHE_SCOPE.studentTests
      ]
    });
  }
};
