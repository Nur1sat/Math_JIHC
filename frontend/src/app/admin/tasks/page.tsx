"use client";

import { startTransition, useDeferredValue, useEffect, useState } from "react";

import { AdminShell } from "@/components/admin-shell";
import { ErrorPanel, LoadingPanel, MaterialIcon } from "@/components/ui";
import { apiClient } from "@/lib/api-client";
import { useProtectedRoute } from "@/lib/session";
import type { TaskItem, TaskListPayload } from "@/lib/types";

type TaskFormState = {
  title: string;
  description: string;
  prompt: string;
  answer: string;
  gradeLevel: string;
  category: string;
  difficulty: string;
  status: string;
  estimatedMinutes: string;
  questionType: "numeric" | "choice";
  choices: string;
};

const emptyForm: TaskFormState = {
  title: "",
  description: "",
  prompt: "",
  answer: "",
  gradeLevel: "Grade 1",
  category: "Logic",
  difficulty: "Beginner",
  status: "draft",
  estimatedMinutes: "15",
  questionType: "numeric",
  choices: ""
};

function buildFormData(form: TaskFormState, file: File | null) {
  const formData = new FormData();
  formData.set("title", form.title);
  formData.set("description", form.description);
  formData.set("prompt", form.prompt);
  formData.set("answer", form.answer);
  formData.set("grade_level", form.gradeLevel);
  formData.set("category", form.category);
  formData.set("difficulty", form.difficulty);
  formData.set("status_value", form.status);
  formData.set("estimated_minutes", form.estimatedMinutes);
  formData.set("question_type", form.questionType);
  if (form.questionType === "choice" && form.choices.trim()) {
    formData.set(
      "choices_json",
      JSON.stringify(
        form.choices
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean)
      )
    );
  }
  if (file) {
    formData.set("image", file);
  }
  return formData;
}

function hydrateForm(task: TaskItem): TaskFormState {
  return {
    title: task.title,
    description: task.description,
    prompt: task.prompt,
    answer: task.answer,
    gradeLevel: task.gradeLevel,
    category: task.category,
    difficulty: task.difficulty,
    status: task.status,
    estimatedMinutes: String(task.estimatedMinutes),
    questionType: task.questionType,
    choices: task.choices.join(", ")
  };
}

export default function AdminTasksPage() {
  const { ready } = useProtectedRoute("admin", "/admin/login");
  const [mode, setMode] = useState<"manual" | "json">("manual");
  const [data, setData] = useState<TaskListPayload | null>(null);
  const [search, setSearch] = useState("");
  const deferredSearch = useDeferredValue(search);
  const [form, setForm] = useState<TaskFormState>(emptyForm);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [jsonFile, setJsonFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!ready) {
      return;
    }
    setLoading(true);
    apiClient
      .getAdminTasks(deferredSearch)
      .then((payload) => {
        setData(payload);
        setError(null);
      })
      .catch((requestError) =>
        setError(requestError instanceof Error ? requestError.message : "Unable to load tasks")
      )
      .finally(() => setLoading(false));
  }, [deferredSearch, ready]);

  function resetManual() {
    setEditingId(null);
    setForm(emptyForm);
    setImageFile(null);
    setImagePreview(null);
  }

  function refreshList() {
    startTransition(() => {
      apiClient
        .getAdminTasks(deferredSearch)
        .then(setData)
        .catch((requestError) =>
          setError(requestError instanceof Error ? requestError.message : "Unable to refresh tasks")
        );
    });
  }

  async function handleManualSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const payload = buildFormData(form, imageFile);
      if (editingId) {
        await apiClient.updateTask(editingId, payload);
      } else {
        await apiClient.createTask(payload);
      }
      resetManual();
      refreshList();
    } catch (submissionError) {
      setError(submissionError instanceof Error ? submissionError.message : "Unable to save task");
    } finally {
      setSaving(false);
    }
  }

  async function handleJsonImport(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!jsonFile) {
      setError("Select a JSON file");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const payload = new FormData();
      payload.set("file", jsonFile);
      await apiClient.importTasksJson(payload);
      setJsonFile(null);
      refreshList();
    } catch (submissionError) {
      setError(
        submissionError instanceof Error ? submissionError.message : "Unable to import JSON"
      );
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(taskId: number) {
    if (!window.confirm("Delete this task?")) {
      return;
    }
    try {
      await apiClient.deleteTask(taskId);
      refreshList();
      if (editingId === taskId) {
        resetManual();
      }
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to delete task");
    }
  }

  return (
    <AdminShell active="tasks">
      <div className="mx-auto w-full max-w-7xl p-6 md:p-10">
        <div className="mb-8">
          <h2 className="text-[2.5rem] font-black tracking-tight text-on-surface">
            Task Management
          </h2>
        </div>
        {error ? (
          <div className="mb-6">
            <ErrorPanel message={error} />
          </div>
        ) : null}
        <div className="grid grid-cols-1 items-start gap-8 lg:grid-cols-12">
          <section className="rounded-xl bg-surface-container-lowest p-8 shadow-soft lg:col-span-5">
            <div className="mb-6 flex items-center justify-between">
              <h3 className="text-xl font-black text-on-surface">
                {editingId ? "Edit Task" : "Add Task"}
              </h3>
              <div className="flex rounded-full bg-surface-container p-1">
                <button
                  className={`rounded-full px-4 py-2 text-sm font-bold ${
                    mode === "manual" ? "bg-primary text-on-primary" : "text-secondary"
                  }`}
                  onClick={() => setMode("manual")}
                  type="button"
                >
                  Vruchnuyu
                </button>
                <button
                  className={`rounded-full px-4 py-2 text-sm font-bold ${
                    mode === "json" ? "bg-primary text-on-primary" : "text-secondary"
                  }`}
                  onClick={() => {
                    setMode("json");
                    setEditingId(null);
                  }}
                  type="button"
                >
                  JSON file
                </button>
              </div>
            </div>
            {mode === "manual" ? (
              <form className="space-y-6" onSubmit={handleManualSubmit}>
                <Field label="Title">
                  <input
                    className={inputClass}
                    onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))}
                    type="text"
                    value={form.title}
                  />
                </Field>
                <Field label="Description">
                  <textarea
                    className={inputClass}
                    onChange={(event) =>
                      setForm((current) => ({ ...current, description: event.target.value }))
                    }
                    rows={3}
                    value={form.description}
                  />
                </Field>
                <Field label="Prompt">
                  <textarea
                    className={inputClass}
                    onChange={(event) => setForm((current) => ({ ...current, prompt: event.target.value }))}
                    rows={3}
                    value={form.prompt}
                  />
                </Field>
                <div className="grid grid-cols-2 gap-4">
                  <Field label="Answer">
                    <input
                      className={inputClass}
                      onChange={(event) => setForm((current) => ({ ...current, answer: event.target.value }))}
                      type="text"
                      value={form.answer}
                    />
                  </Field>
                  <Field label="Grade">
                    <select
                      className={inputClass}
                      onChange={(event) =>
                        setForm((current) => ({ ...current, gradeLevel: event.target.value }))
                      }
                      value={form.gradeLevel}
                    >
                      <option>Grade 1</option>
                      <option>Grade 2</option>
                      <option>Grade 3</option>
                      <option>Grade 4</option>
                    </select>
                  </Field>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <Field label="Category">
                    <input
                      className={inputClass}
                      onChange={(event) =>
                        setForm((current) => ({ ...current, category: event.target.value }))
                      }
                      type="text"
                      value={form.category}
                    />
                  </Field>
                  <Field label="Difficulty">
                    <select
                      className={inputClass}
                      onChange={(event) =>
                        setForm((current) => ({ ...current, difficulty: event.target.value }))
                      }
                      value={form.difficulty}
                    >
                      <option>Beginner</option>
                      <option>Intermediate</option>
                      <option>Advanced</option>
                    </select>
                  </Field>
                </div>
                <div className="grid grid-cols-3 gap-4">
                  <Field label="Status">
                    <select
                      className={inputClass}
                      onChange={(event) => setForm((current) => ({ ...current, status: event.target.value }))}
                      value={form.status}
                    >
                      <option value="draft">Draft</option>
                      <option value="active">Active</option>
                    </select>
                  </Field>
                  <Field label="Minutes">
                    <input
                      className={inputClass}
                      min="1"
                      onChange={(event) =>
                        setForm((current) => ({ ...current, estimatedMinutes: event.target.value }))
                      }
                      type="number"
                      value={form.estimatedMinutes}
                    />
                  </Field>
                  <Field label="Type">
                    <select
                      className={inputClass}
                      onChange={(event) =>
                        setForm((current) => ({
                          ...current,
                          questionType: event.target.value as TaskFormState["questionType"]
                        }))
                      }
                      value={form.questionType}
                    >
                      <option value="numeric">Numeric</option>
                      <option value="choice">Choice</option>
                    </select>
                  </Field>
                </div>
                {form.questionType === "choice" ? (
                  <Field label="Choices">
                    <input
                      className={inputClass}
                      onChange={(event) =>
                        setForm((current) => ({ ...current, choices: event.target.value }))
                      }
                      placeholder="1, 2, 3"
                      type="text"
                      value={form.choices}
                    />
                  </Field>
                ) : null}
                <Field label="Image">
                  <label className="group relative flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed border-outline-variant p-8 transition-colors hover:bg-surface-container-low">
                    <MaterialIcon className="mb-2 text-4xl text-outline" icon="cloud_upload" />
                    <p className="text-sm font-medium text-secondary">
                      {imageFile ? imageFile.name : "Upload image"}
                    </p>
                    <input
                      className="absolute inset-0 opacity-0"
                      onChange={(event) => {
                        const file = event.target.files?.[0] ?? null;
                        setImageFile(file);
                        setImagePreview(file ? URL.createObjectURL(file) : null);
                      }}
                      type="file"
                    />
                  </label>
                </Field>
                {imagePreview ? (
                  <img alt="Task preview" className="max-h-48 rounded-2xl object-cover" src={imagePreview} />
                ) : null}
                <div className="flex gap-4">
                  <button
                    className="flex-1 rounded-full bg-gradient-to-r from-primary to-primary-container py-4 font-bold text-on-primary shadow-lg transition-all hover:brightness-105 active:scale-95"
                    disabled={saving}
                    type="submit"
                  >
                    {saving ? "Saving..." : editingId ? "Update" : "Save"}
                  </button>
                  <button
                    className="rounded-full bg-secondary-container px-8 font-bold text-on-secondary-container transition-all hover:brightness-95"
                    onClick={resetManual}
                    type="button"
                  >
                    Reset
                  </button>
                </div>
              </form>
            ) : (
              <form className="space-y-6" onSubmit={handleJsonImport}>
                <label className="group relative flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed border-outline-variant p-10 transition-colors hover:bg-surface-container-low">
                  <MaterialIcon className="mb-2 text-4xl text-outline" icon="upload_file" />
                  <p className="text-sm font-medium text-secondary">
                    {jsonFile ? jsonFile.name : "Upload JSON"}
                  </p>
                  <input
                    accept=".json,application/json"
                    className="absolute inset-0 opacity-0"
                    onChange={(event) => setJsonFile(event.target.files?.[0] ?? null)}
                    type="file"
                  />
                </label>
                <button
                  className="w-full rounded-full bg-gradient-to-r from-primary to-primary-container py-4 font-bold text-on-primary shadow-lg transition-all hover:brightness-105 active:scale-95"
                  disabled={saving}
                  type="submit"
                >
                  {saving ? "Importing..." : "Import"}
                </button>
              </form>
            )}
          </section>
          <section className="overflow-hidden rounded-xl bg-surface-container-low lg:col-span-7">
            <div className="flex items-end justify-between p-8 pb-4">
              <div>
                <h3 className="text-xl font-black text-on-surface">Tasks</h3>
                <p className="text-sm text-secondary">
                  {data?.summary.total ?? 0} total · {data?.summary.active ?? 0} active · {data?.summary.drafts ?? 0} drafts
                </p>
              </div>
              <div className="relative w-full max-w-xs">
                <MaterialIcon className="absolute left-3 top-1/2 -translate-y-1/2 text-outline" icon="search" />
                <input
                  className="w-full rounded-full bg-white py-2 pl-10 pr-4 text-sm outline-none ring-primary/20 transition-all focus:ring-2"
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Search"
                  type="text"
                  value={search}
                />
              </div>
            </div>
            {loading && !data ? (
              <div className="p-8">
                <LoadingPanel label="Loading..." />
              </div>
            ) : null}
            <div className="space-y-3 px-8 pb-8">
              {data?.items.map((task) => (
                <div
                  className="grid grid-cols-[1.7fr,0.8fr,0.8fr,0.8fr] items-center rounded-xl bg-surface-container-lowest px-4 py-4 transition-transform hover:-translate-y-0.5"
                  key={task.id}
                >
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary-container/20 text-primary">
                      <MaterialIcon icon={task.questionType === "choice" ? "pie_chart" : "functions"} />
                    </div>
                    <div>
                      <p className="font-bold text-on-surface">{task.title}</p>
                      <p className="w-48 truncate text-xs text-secondary">{task.gradeLevel}</p>
                    </div>
                  </div>
                  <span className="text-sm text-secondary">{task.category}</span>
                  <span className={`text-sm font-bold ${task.status === "active" ? "text-primary" : "text-secondary"}`}>
                    {task.status}
                  </span>
                  <div className="flex justify-end gap-2">
                    <button
                      className="rounded-full p-2 text-secondary transition-colors hover:bg-primary/10 hover:text-primary"
                      onClick={() => {
                        setMode("manual");
                        setEditingId(task.id);
                        setForm(hydrateForm(task));
                        setImageFile(null);
                        setImagePreview(task.imageUrl);
                      }}
                      type="button"
                    >
                      <MaterialIcon icon="edit" />
                    </button>
                    <button
                      className="rounded-full p-2 text-secondary transition-colors hover:bg-error/10 hover:text-error"
                      onClick={() => handleDelete(task.id)}
                      type="button"
                    >
                      <MaterialIcon icon="delete" />
                    </button>
                  </div>
                </div>
              ))}
              {!data?.items.length && !loading ? (
                <div className="rounded-2xl bg-surface-container-lowest p-8 text-center text-secondary">
                  No tasks.
                </div>
              ) : null}
            </div>
          </section>
        </div>
      </div>
    </AdminShell>
  );
}

function Field({
  label,
  children
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-2">
      <label className="ml-1 block text-sm font-bold text-secondary">{label}</label>
      {children}
    </div>
  );
}

const inputClass =
  "w-full rounded-xl bg-surface-container-high px-4 py-3 outline-none ring-primary/20 transition-all focus:bg-surface-container-lowest focus:ring-2";
