"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { StudentShell } from "@/components/student-shell";
import { ErrorPanel, LoadingPanel, MaterialIcon } from "@/components/ui";
import { apiClient } from "@/lib/api-client";
import { useProtectedRoute } from "@/lib/session";
import type { StudentTestPayload, SubmissionResponse } from "@/lib/types";

export default function StudentTestPage() {
  const params = useParams<{ id: string }>();
  const { ready } = useProtectedRoute("student", "/");
  const [data, setData] = useState<StudentTestPayload | null>(null);
  const [answer, setAnswer] = useState("");
  const [result, setResult] = useState<SubmissionResponse | null>(null);
  const [hint, setHint] = useState<string | null>(null);
  const [hintLevel, setHintLevel] = useState(0);
  const [hintLoading, setHintLoading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!ready || !params.id) {
      return;
    }
    apiClient
      .getStudentTest(params.id)
      .then((payload) => {
        setData(payload);
        setAnswer(payload.lastSubmission?.answer ?? "");
        setHint(null);
        setHintLevel(0);
      })
      .catch((requestError) =>
        setError(requestError instanceof Error ? requestError.message : "Тапсырма жүктелмеді")
      );
  }, [params.id, ready]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!params.id || !answer.trim()) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const submission = await apiClient.submitStudentTest(params.id, answer.trim());
      setResult(submission);
    } catch (submissionError) {
      setError(submissionError instanceof Error ? submissionError.message : "Жауапты жіберу мүмкін болмады");
    } finally {
      setLoading(false);
    }
  }

  async function handleHint() {
    if (!params.id) {
      return;
    }
    const nextLevel = Math.min(hintLevel + 1, 3);
    setHintLoading(true);
    setError(null);
    try {
      const payload = await apiClient.getStudentHint(params.id, nextLevel, answer);
      setHint(payload.hint);
      setHintLevel(payload.level);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Көмек алу мүмкін болмады");
    } finally {
      setHintLoading(false);
    }
  }

  return (
    <StudentShell active="tasks">
      <section className="mx-auto grid max-w-7xl grid-cols-1 gap-8 px-6 pb-12 lg:grid-cols-12">
        {!ready || (!data && !error) ? <LoadingPanel label="Тапсырма жүктелуде..." /> : null}
        {error ? <ErrorPanel message={error} /> : null}
        {data ? (
          <>
            <aside className="space-y-6 lg:col-span-3">
              <div className="rounded-xl bg-surface-container-lowest p-6 shadow-soft">
                <p className="text-xs font-bold uppercase tracking-wider text-secondary">Тапсырма</p>
                <p className="mt-3 text-2xl font-black text-on-surface">{data.task.title}</p>
              </div>
              <div className="flex items-center gap-4 rounded-xl bg-surface-container-low p-6">
                <div className="rounded-full bg-tertiary-container/20 p-3">
                  <MaterialIcon className="text-tertiary" fill icon="timer" />
                </div>
                <div>
                  <span className="block text-xs font-bold uppercase text-secondary">
                    Уақыт
                  </span>
                  <span className="text-xl font-bold text-on-surface">
                    {data.meta.timeRemaining}
                  </span>
                </div>
              </div>
              <div className="rounded-xl border border-outline-variant/10 bg-surface-container-lowest p-6">
                <div className="grid gap-4 text-sm">
                  <div className="flex items-center justify-between">
                    <span className="text-secondary">Сынып</span>
                    <span className="font-semibold text-on-surface">{data.task.gradeLevel}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-secondary">Тақырып</span>
                    <span className="font-semibold text-on-surface">{data.task.category}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-secondary">Деңгей</span>
                    <span className="font-semibold text-on-surface">{data.task.difficulty}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-secondary">Рет саны</span>
                    <span className="font-semibold text-on-surface">
                      {data.meta.questionNumber}/{data.meta.totalQuestions}
                    </span>
                  </div>
                </div>
              </div>
              {data.lastSubmission ? (
                <div className="rounded-xl border border-outline-variant/10 bg-surface-container-lowest p-6">
                  <p className="text-xs font-bold uppercase tracking-wider text-secondary">
                    Соңғы жауап
                  </p>
                  <p className="mt-3 text-lg font-bold text-on-surface">
                    {data.lastSubmission.answer}
                  </p>
                  <p className="mt-2 text-sm text-secondary">
                    {data.lastSubmission.score}%{" "}
                    {data.lastSubmission.isCorrect ? "дұрыс" : "қате"}
                  </p>
                </div>
              ) : null}
              <Link
                className="flex items-center justify-center gap-2 rounded-full bg-surface-container-low px-6 py-3 font-bold text-secondary transition-colors hover:bg-surface-container-high"
                href="/student/dashboard#tasks"
              >
                <MaterialIcon icon="arrow_back" />
                Артқа
              </Link>
            </aside>
            <section className="lg:col-span-9">
              <div className="flex min-h-[600px] flex-col rounded-xl bg-surface-container-lowest p-8 shadow-soft lg:p-12">
                <div className="mb-8">
                  <span className="mb-4 inline-block rounded-lg bg-surface-container-high px-3 py-1 text-xs font-bold uppercase tracking-widest text-secondary">
                    {data.task.category}
                  </span>
                  <h1 className="text-2xl font-bold leading-tight text-on-surface lg:text-3xl">
                    {data.task.prompt}
                  </h1>
                </div>
                {data.task.documentUrl ? (
                  <a
                    className="mb-6 inline-flex w-fit items-center gap-2 rounded-full bg-secondary-container px-5 py-3 text-sm font-bold text-on-secondary-container transition-colors hover:brightness-95"
                    href={data.task.documentUrl}
                    rel="noreferrer"
                    target="_blank"
                  >
                    <MaterialIcon icon="description" />
                    {data.task.documentName ?? "DOCX материал"}
                  </a>
                ) : null}
                <div className="mb-8 rounded-2xl bg-surface-container-low p-4 sm:p-8">
                  {data.task.contentHtml ? (
                    <iframe
                      className="h-[760px] w-full rounded-2xl border border-outline-variant bg-white"
                      sandbox="allow-scripts"
                      srcDoc={data.task.contentHtml}
                      title={data.task.title}
                    />
                  ) : data.task.imageUrl ? (
                    <img
                      alt={data.task.title}
                      className="mx-auto max-h-[360px] rounded-2xl object-contain"
                      src={data.task.imageUrl}
                    />
                  ) : (
                    <div className="flex min-h-[220px] items-center justify-center rounded-2xl border border-dashed border-outline-variant bg-white">
                      <div className="text-center">
                        <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-primary/10 text-primary">
                          <MaterialIcon
                            icon={data.task.questionType === "choice" ? "quiz" : "calculate"}
                          />
                        </div>
                        <p className="font-semibold text-on-surface">{data.task.title}</p>
                      </div>
                    </div>
                  )}
                </div>
                <form className="w-full max-w-2xl self-center" onSubmit={handleSubmit}>
                  {data.task.questionType === "choice" ? (
                    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
                      {data.task.choices.map((choice) => {
                        const selected = answer === choice;
                        return (
                          <button
                            className={`rounded-2xl px-6 py-5 text-lg font-bold transition-all ${
                              selected
                                ? "scale-[1.02] bg-secondary-container text-on-secondary-container shadow-md"
                                : "bg-surface-container-high text-on-surface hover:-translate-y-0.5 hover:bg-surface-container-highest"
                            }`}
                            key={choice}
                            onClick={() => setAnswer(choice)}
                            type="button"
                          >
                            {choice}
                          </button>
                        );
                      })}
                    </div>
                  ) : (
                    <>
                      <label
                        className="mb-3 block text-center text-sm font-bold uppercase text-secondary"
                        htmlFor="answer"
                      >
                        Жауап
                      </label>
                      <div className="relative">
                        <input
                          className="w-full rounded-xl bg-surface-container-high px-8 py-6 text-center text-3xl font-black text-primary outline-none transition-all focus:bg-white focus:ring-4 focus:ring-primary-container/20"
                          id="answer"
                          onChange={(event) => setAnswer(event.target.value)}
                          placeholder="Жауапты жазыңыз"
                          type="text"
                          value={answer}
                        />
                        <div className="absolute right-4 top-1/2 -translate-y-1/2 rounded-lg bg-secondary-container p-2">
                          <MaterialIcon className="text-on-secondary-container" icon="calculate" />
                        </div>
                      </div>
                    </>
                  )}
                  {result ? (
                    <div
                      className={`mt-4 rounded-xl px-4 py-3 text-sm font-semibold ${
                        result.isCorrect
                          ? "bg-primary/10 text-primary"
                          : "bg-error-container text-on-error-container"
                      }`}
                    >
                      {result.message}
                    </div>
                  ) : null}
                  {hint ? (
                    <div className="mt-4 rounded-xl bg-tertiary-container/20 px-4 py-3 text-sm font-semibold text-on-surface">
                      {hint}
                    </div>
                  ) : null}
                  <div className="mt-10 flex flex-col justify-end gap-3 sm:flex-row">
                    <button
                      className="inline-flex items-center justify-center gap-2 rounded-full bg-surface-container-high px-6 py-4 font-bold text-secondary transition-all hover:bg-surface-container-highest active:scale-95"
                      disabled={hintLoading}
                      onClick={handleHint}
                      type="button"
                    >
                      <MaterialIcon icon="psychology" />
                      {hintLoading ? "Ойлануда..." : hintLevel ? "Тағы көмек" : "Көмек алу"}
                    </button>
                    <button
                      className="flex items-center gap-2 rounded-full bg-primary px-10 py-4 font-bold text-on-primary shadow-lg transition-all hover:bg-primary-container active:scale-95"
                      disabled={loading}
                      type="submit"
                    >
                      {loading ? "Жіберілуде..." : "Жауап беру"}
                      <MaterialIcon icon="check_circle" />
                    </button>
                  </div>
                </form>
              </div>
            </section>
          </>
        ) : null}
      </section>
    </StudentShell>
  );
}
