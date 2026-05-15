"use client";

import { useEffect, useState } from "react";

import { AdminShell } from "@/components/admin-shell";
import { ErrorPanel, LoadingPanel } from "@/components/ui";
import { apiClient } from "@/lib/api-client";
import { useProtectedRoute } from "@/lib/session";
import type { AdminDashboardPayload } from "@/lib/types";

export default function AdminDashboardPage() {
  const { ready } = useProtectedRoute("admin", "/admin/login");
  const [data, setData] = useState<AdminDashboardPayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!ready) {
      return;
    }
    apiClient
      .getAdminDashboard()
      .then(setData)
      .catch((requestError) =>
        setError(requestError instanceof Error ? requestError.message : "Панель жүктелмеді")
      );
  }, [ready]);

  return (
    <AdminShell active="dashboard">
      <section className="mx-auto max-w-7xl px-8 py-8">
        {!ready || (!data && !error) ? <LoadingPanel label="Жүктелуде..." /> : null}
        {error ? <ErrorPanel message={error} /> : null}
        {data ? (
          <>
            <div className="mb-8">
              <h2 className="text-3xl font-black text-on-surface">Әкімші панелі</h2>
            </div>
            <div className="mb-8 grid grid-cols-1 gap-6 md:grid-cols-5">
              <MetricCard label="Оқушылар" value={data.metrics.activeStudents} />
              <MetricCard label="Тапсырмалар" value={data.metrics.totalTests} />
              <MetricCard label="Белсенді" value={data.metrics.activeTasks} />
              <MetricCard label="Жоба" value={data.metrics.draftTasks} />
              <MetricCard accent label="Орташа балл" value={`${data.metrics.averageScore}%`} />
            </div>
            <div className="grid grid-cols-1 gap-8 lg:grid-cols-2">
              <section className="rounded-2xl bg-surface-container-lowest p-8 shadow-soft">
                <h3 className="mb-6 text-xl font-black text-on-surface">Соңғы нәтижелер</h3>
                <div className="space-y-4">
                  {data.recentResults.length ? (
                    data.recentResults.map((result) => (
                      <div className="rounded-xl bg-surface-container-low p-4" key={`${result.studentName}-${result.timeLabel}`}>
                        <div className="flex items-start justify-between gap-4">
                          <div>
                            <p className="font-bold text-on-surface">{result.studentName}</p>
                            <p className="text-sm text-secondary">{result.taskTitle}</p>
                          </div>
                          <div className="text-right">
                            <p className="font-bold text-primary">{result.score}%</p>
                            <p className="text-xs text-secondary">
                              {new Date(result.timeLabel).toLocaleString()}
                            </p>
                          </div>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="rounded-xl bg-surface-container-low p-4 text-secondary">
                      Әлі нәтиже жоқ.
                    </div>
                  )}
                </div>
              </section>
              <section className="rounded-2xl bg-surface-container-lowest p-8 shadow-soft">
                <div className="mb-6 flex items-center justify-between">
                  <h3 className="text-xl font-black text-on-surface">Соңғы тапсырмалар</h3>
                  <p className="text-sm font-bold text-secondary">
                    Жауаптар: {data.metrics.totalSubmissions}
                  </p>
                </div>
                <div className="space-y-4">
                  {data.recentTasks.map((task) => (
                    <div className="rounded-xl bg-surface-container-low p-4" key={task.id}>
                      <div className="flex items-start justify-between gap-4">
                        <div>
                          <p className="font-bold text-on-surface">{task.title}</p>
                          <p className="text-sm text-secondary">
                            {task.gradeLevel} · {task.category}
                          </p>
                        </div>
                        <div className="text-right">
                          <p
                            className={`font-bold ${
                              task.status === "active" ? "text-primary" : "text-secondary"
                            }`}
                          >
                            {task.status === "active" ? "Белсенді" : "Жоба"}
                          </p>
                          <p className="text-xs text-secondary">
                            {new Date(task.updatedAt).toLocaleDateString()}
                          </p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            </div>
          </>
        ) : null}
      </section>
    </AdminShell>
  );
}

function MetricCard({
  label,
  value,
  accent = false
}: {
  label: string;
  value: number | string;
  accent?: boolean;
}) {
  return (
    <div
      className={`rounded-2xl p-6 shadow-soft ${
        accent ? "bg-primary text-on-primary" : "bg-surface-container-lowest"
      }`}
    >
      <p
        className={`text-xs font-bold uppercase tracking-wider ${
          accent ? "text-white/70" : "text-secondary"
        }`}
      >
        {label}
      </p>
      <p className={`mt-3 text-4xl font-black ${accent ? "text-on-primary" : "text-primary"}`}>
        {value}
      </p>
    </div>
  );
}
