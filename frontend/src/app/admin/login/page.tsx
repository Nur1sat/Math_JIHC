"use client";

import Link from "next/link";

import { LoginForm } from "@/components/login-form";
import { BrandIdentity } from "@/components/ui";
import { useGuestRoute } from "@/lib/session";

export default function AdminLoginPage() {
  const { ready } = useGuestRoute();

  if (!ready) {
    return null;
  }

  return (
    <main className="bg-auth-gradient relative flex min-h-screen items-center justify-center overflow-hidden px-6 py-12">
      <div className="absolute left-[-8%] top-[-8%] h-96 w-96 rounded-full bg-primary/5 blur-3xl" />
      <div className="absolute bottom-[-8%] right-[-8%] h-96 w-96 rounded-full bg-tertiary/5 blur-3xl" />
      <div className="relative z-10 w-full max-w-md">
        <div className="mb-10 flex flex-col items-center">
          <BrandIdentity className="mb-2" />
          <p className="mt-1 text-sm font-medium uppercase tracking-widest text-outline">Admin</p>
        </div>
        <div className="rounded-[2rem] border border-outline-variant/10 bg-surface-container-lowest p-8 shadow-soft">
          <div className="mb-8 flex items-center justify-between">
            <h2 className="text-2xl font-bold text-on-surface">Admin</h2>
            <Link className="text-sm font-bold text-primary" href="/">
              Student
            </Link>
          </div>
          <LoginForm
            redirectTo="/admin/dashboard"
            role="admin"
            submitLabel="Enter"
            title=""
          />
        </div>
      </div>
    </main>
  );
}
