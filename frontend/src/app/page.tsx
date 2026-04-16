"use client";

import Link from "next/link";

import { LoginForm } from "@/components/login-form";
import { BrandIdentity } from "@/components/ui";
import { useGuestRoute } from "@/lib/session";

export default function StudentLoginPage() {
  const { ready } = useGuestRoute();

  if (!ready) {
    return null;
  }

  return (
    <main className="bg-auth-gradient flex min-h-screen items-center justify-center px-4 py-8 md:px-8">
      <div className="grid w-full max-w-6xl overflow-hidden rounded-[2rem] bg-surface-container-lowest shadow-[0_20px_60px_rgba(46,108,0,0.12)] lg:grid-cols-12">
        <section className="relative flex min-h-[420px] flex-col justify-between overflow-hidden bg-primary p-8 text-on-primary lg:col-span-7 lg:min-h-[760px] lg:p-12">
          <div className="absolute right-[-8%] top-[-8%] h-64 w-64 rounded-full bg-secondary-container/20 blur-3xl" />
          <div className="absolute bottom-[-10%] left-[-8%] h-96 w-96 rounded-full bg-tertiary/20 blur-3xl" />
          <div className="relative z-10">
            <div className="mb-10 flex items-center gap-3">
              <BrandIdentity light />
            </div>
            <h1 className="max-w-xl text-4xl font-black leading-tight md:text-5xl lg:text-6xl">
              Student
            </h1>
            <p className="mt-6 max-w-md text-lg text-primary-fixed">Sign in and continue.</p>
          </div>
          <div className="relative z-10 mt-12 flex justify-center lg:justify-start">
            <div className="w-full max-w-md rounded-[2rem] border border-white/10 bg-white/10 p-8 backdrop-blur">
              <div className="mb-8 flex items-center justify-center rounded-[2rem] bg-white/90 p-10">
                <img alt="Math_JIHC logo" className="h-40 w-40 object-contain" src="/math_jihc-logo.svg" />
              </div>
              <div className="grid grid-cols-3 gap-3 text-center text-sm font-bold">
                <div className="rounded-2xl bg-white/10 px-4 py-5">Tasks</div>
                <div className="rounded-2xl bg-white/10 px-4 py-5">Results</div>
                <div className="rounded-2xl bg-white/10 px-4 py-5">Progress</div>
              </div>
            </div>
          </div>
        </section>
        <section className="flex items-center bg-white p-8 lg:col-span-5 lg:p-16">
          <div className="mx-auto w-full max-w-md">
            <div className="mb-8 flex items-center justify-between">
              <h2 className="text-3xl font-black text-on-surface">Student</h2>
              <Link className="text-sm font-bold text-primary" href="/admin/login">
                Admin
              </Link>
            </div>
            <LoginForm
              redirectTo="/student/dashboard"
              role="student"
              submitLabel="Enter"
              title=""
            />
          </div>
        </section>
      </div>
    </main>
  );
}
