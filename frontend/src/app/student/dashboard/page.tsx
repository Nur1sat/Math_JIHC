"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { StudentShell } from "@/components/student-shell";
import { ErrorPanel, LoadingPanel, MaterialIcon } from "@/components/ui";
import { apiClient } from "@/lib/api-client";
import { useProtectedRoute } from "@/lib/session";
import type { StudentDashboardPayload } from "@/lib/types";

export default function StudentDashboardPage() {
  const { ready } = useProtectedRoute("student", "/");
  const [data, setData] = useState<StudentDashboardPayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!ready) {
      return;
    }
    apiClient
      .getStudentDashboard()
      .then(setData)
      .catch((requestError) => {
        setError(
          requestError instanceof Error ? requestError.message : "Unable to load dashboard"
        );
      });
  }, [ready]);

  return (
    <StudentShell active="dashboard">
      <section className="mx-auto w-full max-w-7xl px-8 py-8">
        {!ready || (!data && !error) ? <LoadingPanel label="Loading..." /> : null}
        {error ? <ErrorPanel message={error} /> : null}
        {data ? (
          <>
            <div className="mb-8">
              <h2 className="text-3xl font-black text-on-surface">{data.user.fullName}</h2>
              <p className="mt-2 text-secondary">{data.user.gradeLabel}</p>
            </div>
            <div className="mb-8 grid grid-cols-1 gap-6 md:grid-cols-4">
              <div className="rounded-2xl bg-surface-container-lowest p-6 shadow-soft">
                <p className="text-xs font-bold uppercase tracking-wider text-secondary">Active</p>
                <p className="mt-3 text-4xl font-black text-primary">{data.summary.activeTasks}</p>
              </div>
              <div className="rounded-2xl bg-surface-container-lowest p-6 shadow-soft">
                <p className="text-xs font-bold uppercase tracking-wider text-secondary">Completed</p>
                <p className="mt-3 text-4xl font-black text-primary">
                  {data.summary.completedTasks}
                </p>
              </div>
              <div className="rounded-2xl bg-surface-container-lowest p-6 shadow-soft">
                <p className="text-xs font-bold uppercase tracking-wider text-secondary">Pending</p>
                <p className="mt-3 text-4xl font-black text-primary">{data.summary.pendingTasks}</p>
              </div>
              <div className="rounded-2xl bg-primary p-6 text-on-primary shadow-lg shadow-primary/20">
                <p className="text-xs font-bold uppercase tracking-wider text-white/70">Avg. Score</p>
                <p className="mt-3 text-4xl font-black">{data.summary.averageScore}%</p>
              </div>
            </div>
            <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
              <div className="rounded-2xl bg-surface-container-lowest p-8 shadow-soft lg:col-span-2">
                <div className="mb-6 flex items-center justify-between">
                  <h3 className="text-xl font-black text-on-surface">Next Task</h3>
                  {data.nextTask ? (
                    <Link className="text-sm font-bold text-primary" href={`/student/tests/${data.nextTask.id}`}>
                      Open
                    </Link>
                  ) : null}
                </div>
                {data.nextTask ? (
                  <div className="rounded-2xl bg-surface-container-low p-6">
                    <div className="mb-4 flex items-center gap-3">
                      <div className="rounded-2xl bg-primary-container p-3 text-on-primary-container">
                        <MaterialIcon icon="play_arrow" />
                      </div>
                      <div>
                        <p className="font-bold text-on-surface">{data.nextTask.title}</p>
                        <p className="text-sm text-secondary">
                          {data.nextTask.gradeLevel} · {data.nextTask.category}
                        </p>
                      </div>
                    </div>
                    <p className="mb-6 text-on-surface-variant">{data.nextTask.prompt}</p>
                    <Link
                      className="inline-flex items-center gap-2 rounded-full bg-primary px-6 py-3 font-bold text-on-primary transition-colors hover:bg-primary-container"
                      href={`/student/tests/${data.nextTask.id}`}
                    >
                      Start
                      <MaterialIcon icon="arrow_forward" />
                    </Link>
                  </div>
                ) : (
                  <div className="rounded-2xl bg-surface-container-low p-6 text-secondary">
                    No pending tasks.
                  </div>
                )}
              </div>
              <div className="rounded-2xl bg-surface-container-lowest p-8 shadow-soft">
                <h3 className="mb-6 text-xl font-black text-on-surface">Recent Results</h3>
                <div className="space-y-4">
                  {data.recentResults.length ? (
                    data.recentResults.map((result) => (
                      <div className="rounded-xl bg-surface-container-low p-4" key={`${result.taskId}-${result.submittedAt}`}>
                        <p className="font-bold text-on-surface">{result.taskTitle}</p>
                        <div className="mt-2 flex items-center justify-between text-sm">
                          <span className={result.isCorrect ? "font-bold text-primary" : "font-bold text-tertiary"}>
                            {result.score}%
                          </span>
                          <span className="text-secondary">
                            {new Date(result.submittedAt).toLocaleDateString()}
                          </span>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="rounded-xl bg-surface-container-low p-4 text-secondary">
                      No submissions yet.
                    </div>
                  )}
                </div>
              </div>
            </div>
            <div className="mt-10" id="tasks">
              <h3 className="mb-6 text-2xl font-black text-on-surface">Tasks</h3>
              <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-3">
                {data.tests.map((task) => (
                  <div
                    className="flex flex-col rounded-[2rem] border border-transparent bg-surface-container-lowest p-6 shadow-soft transition-all hover:border-primary/10"
                    key={task.id}
                  >
                    {task.imageUrl ? (
                      <div className="mb-6 aspect-video overflow-hidden rounded-2xl">
                        <img alt={task.title} className="h-full w-full object-cover" src={task.imageUrl} />
                      </div>
                    ) : (
                      <div className="mb-6 flex aspect-video items-center justify-center rounded-2xl bg-surface-container">
                        <div className="rounded-full bg-primary/10 p-4 text-primary">
                          <MaterialIcon icon="functions" />
                        </div>
                      </div>
                    )}
                    <h4 className="mb-2 text-lg font-bold">{task.title}</h4>
                    <p className="mb-4 flex-1 text-sm text-on-surface-variant">{task.description}</p>
                    <div className="mb-4 flex items-center justify-between text-sm text-secondary">
                      <span>{task.gradeLevel}</span>
                      <span>{task.estimatedMinutes} min</span>
                    </div>
                    <div className="mb-4 flex items-center justify-between text-sm">
                      <span className={task.completed ? "font-bold text-primary" : "font-bold text-secondary"}>
                        {task.completed
                          ? `Done${task.lastScore !== null && task.lastScore !== undefined ? ` · ${task.lastScore}%` : ""}`
                          : "Open"}
                      </span>
                      <span className="text-secondary">
                        {task.attemptCount
                          ? `${task.attemptCount} attempt${task.attemptCount > 1 ? "s" : ""}`
                          : "No attempts"}
                      </span>
                    </div>
                    <Link
                      className="inline-flex items-center justify-center gap-2 rounded-full bg-primary px-6 py-3 font-bold text-on-primary transition-all hover:bg-primary-container"
                      href={`/student/tests/${task.id}`}
                    >
                      {task.completed ? "Retry" : "Start"}
                      <MaterialIcon icon="arrow_forward" />
                    </Link>
                  </div>
                ))}
              </div>
            </div>
          </>
        ) : null}
      </section>
    </StudentShell>
  );
}
