"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { apiClient } from "@/lib/api-client";
import { writeSession } from "@/lib/session";
import { MaterialIcon } from "@/components/ui";

export function LoginForm({
  role,
  title = "",
  subtitle = "",
  defaultEmail = "",
  defaultPassword = "",
  redirectTo,
  submitLabel
}: {
  role: "student" | "admin";
  title?: string;
  subtitle?: string;
  defaultEmail?: string;
  defaultPassword?: string;
  redirectTo: string;
  submitLabel: string;
}) {
  const router = useRouter();
  const [email, setEmail] = useState(defaultEmail);
  const [password, setPassword] = useState(defaultPassword);
  const [visible, setVisible] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const session = await apiClient.login(email.trim(), password, role);
      writeSession(session);
      router.replace(redirectTo);
    } catch (submissionError) {
      setError(
        submissionError instanceof Error ? submissionError.message : "Unable to sign in"
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="space-y-6" onSubmit={handleSubmit}>
      <div className="space-y-2">
        <label className="ml-1 block text-sm font-semibold text-on-surface-variant" htmlFor={`${role}-email`}>
          Email Address
        </label>
        <div className="group relative">
          <span className="absolute inset-y-0 left-0 flex items-center pl-4 text-outline group-focus-within:text-primary">
            <MaterialIcon icon="alternate_email" />
          </span>
          <input
            className="block w-full rounded-xl bg-surface-container-low px-11 py-3.5 text-on-surface placeholder:text-outline/60 outline-none transition-all focus:border-primary focus:bg-surface-container-high focus:ring-2 focus:ring-primary/20"
            id={`${role}-email`}
            name="email"
            onChange={(event) => setEmail(event.target.value)}
            autoComplete="email"
            placeholder={role === "admin" ? "admin@mathacademy.edu" : "student@oasis.edu"}
            required
            type="email"
            value={email}
          />
        </div>
      </div>
      <div className="space-y-2">
        <label className="px-1 text-sm font-semibold text-on-surface-variant" htmlFor={`${role}-password`}>
          Password
        </label>
        <div className="group relative">
          <span className="absolute inset-y-0 left-0 flex items-center pl-4 text-outline group-focus-within:text-primary">
            <MaterialIcon icon="lock" />
          </span>
          <input
            className="block w-full rounded-xl bg-surface-container-low px-11 py-3.5 text-on-surface placeholder:text-outline/60 outline-none transition-all focus:border-primary focus:bg-surface-container-high focus:ring-2 focus:ring-primary/20"
            id={`${role}-password`}
            name="password"
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="current-password"
            placeholder="••••••••"
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
      {subtitle ? (
        <div className="rounded-xl bg-surface-container px-4 py-3 text-xs font-medium text-secondary">
          {subtitle}
        </div>
      ) : null}
      {error ? (
        <p className="rounded-xl bg-error-container px-4 py-3 text-sm font-semibold text-on-error-container">
          {error}
        </p>
      ) : null}
      <button
        className="flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-primary to-primary-container py-4 font-bold text-on-primary shadow-lg shadow-primary/20 transition-all hover:brightness-105 active:scale-[0.98]"
        disabled={submitting}
        type="submit"
      >
        {submitting ? "Signing in..." : submitLabel}
        <MaterialIcon icon="arrow_forward" />
      </button>
      {title ? <p className="text-center text-sm text-secondary">{title}</p> : null}
    </form>
  );
}
