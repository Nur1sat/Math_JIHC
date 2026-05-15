"use client";

import { type FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { MaterialIcon } from "@/components/ui";
import { apiClient } from "@/lib/api-client";
import { writeSession } from "@/lib/session";

const gradeOptions = [
  "5-сынып",
  "6-сынып",
  "7-сынып",
  "8-сынып",
  "9-сынып",
  "10-сынып",
  "11-сынып"
];

export function RegisterForm() {
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [gradeLabel, setGradeLabel] = useState("7-сынып");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [visible, setVisible] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const session = await apiClient.registerStudent({
        email: email.trim(),
        password,
        fullName: fullName.trim(),
        gradeLabel
      });
      writeSession(session);
      router.replace("/student/dashboard");
    } catch (submissionError) {
      setError(
        submissionError instanceof Error ? submissionError.message : "Тіркелу мүмкін болмады"
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="space-y-5" onSubmit={handleSubmit}>
      <div className="space-y-2">
        <label className="ml-1 block text-sm font-semibold text-on-surface-variant" htmlFor="register-name">
          Аты-жөні
        </label>
        <div className="group relative">
          <span className="absolute inset-y-0 left-0 flex items-center pl-4 text-outline group-focus-within:text-primary">
            <MaterialIcon icon="person" />
          </span>
          <input
            autoComplete="name"
            className="block w-full rounded-xl bg-surface-container-low px-11 py-3.5 text-on-surface placeholder:text-outline/60 outline-none transition-all focus:bg-surface-container-high focus:ring-2 focus:ring-primary/20"
            id="register-name"
            minLength={2}
            onChange={(event) => setFullName(event.target.value)}
            placeholder="Айдана Оқушы"
            required
            type="text"
            value={fullName}
          />
        </div>
      </div>
      <div className="space-y-2">
        <label className="ml-1 block text-sm font-semibold text-on-surface-variant" htmlFor="register-grade">
          Сынып
        </label>
        <div className="group relative">
          <span className="absolute inset-y-0 left-0 flex items-center pl-4 text-outline group-focus-within:text-primary">
            <MaterialIcon icon="school" />
          </span>
          <select
            className="block w-full appearance-none rounded-xl bg-surface-container-low px-11 py-3.5 text-on-surface outline-none transition-all focus:bg-surface-container-high focus:ring-2 focus:ring-primary/20"
            id="register-grade"
            onChange={(event) => setGradeLabel(event.target.value)}
            value={gradeLabel}
          >
            {gradeOptions.map((grade) => (
              <option key={grade} value={grade}>
                {grade}
              </option>
            ))}
          </select>
          <span className="absolute inset-y-0 right-0 flex items-center pr-4 text-outline">
            <MaterialIcon icon="expand_more" />
          </span>
        </div>
      </div>
      <div className="space-y-2">
        <label className="ml-1 block text-sm font-semibold text-on-surface-variant" htmlFor="register-email">
          Электронды пошта
        </label>
        <div className="group relative">
          <span className="absolute inset-y-0 left-0 flex items-center pl-4 text-outline group-focus-within:text-primary">
            <MaterialIcon icon="alternate_email" />
          </span>
          <input
            autoComplete="email"
            className="block w-full rounded-xl bg-surface-container-low px-11 py-3.5 text-on-surface placeholder:text-outline/60 outline-none transition-all focus:bg-surface-container-high focus:ring-2 focus:ring-primary/20"
            id="register-email"
            onChange={(event) => setEmail(event.target.value)}
            placeholder="student@example.com"
            required
            type="email"
            value={email}
          />
        </div>
      </div>
      <div className="space-y-2">
        <label className="ml-1 block text-sm font-semibold text-on-surface-variant" htmlFor="register-password">
          Құпиясөз
        </label>
        <div className="group relative">
          <span className="absolute inset-y-0 left-0 flex items-center pl-4 text-outline group-focus-within:text-primary">
            <MaterialIcon icon="lock" />
          </span>
          <input
            autoComplete="new-password"
            className="block w-full rounded-xl bg-surface-container-low px-11 py-3.5 text-on-surface placeholder:text-outline/60 outline-none transition-all focus:bg-surface-container-high focus:ring-2 focus:ring-primary/20"
            id="register-password"
            minLength={6}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="Кемінде 6 таңба"
            required
            type={visible ? "text" : "password"}
            value={password}
          />
          <button
            className="absolute inset-y-0 right-0 flex items-center pr-4 text-outline transition-colors hover:text-primary"
            onClick={() => setVisible((current) => !current)}
            type="button"
          >
            <MaterialIcon icon={visible ? "visibility_off" : "visibility"} />
          </button>
        </div>
      </div>
      {error ? (
        <p className="rounded-xl bg-error-container px-4 py-3 text-sm font-semibold text-on-error-container">
          {error}
        </p>
      ) : null}
      <button
        className="flex w-full items-center justify-center gap-2 rounded-xl bg-primary py-4 font-bold text-on-primary shadow-lg shadow-primary/20 transition-all hover:bg-primary-container active:scale-[0.98]"
        disabled={submitting}
        type="submit"
      >
        {submitting ? "Тіркелу орындалуда..." : "Тіркелу"}
        <MaterialIcon icon="person_add" />
      </button>
    </form>
  );
}
