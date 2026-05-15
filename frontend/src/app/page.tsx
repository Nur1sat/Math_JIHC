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
              Математикалық ойлау
            </h1>
            <p className="mt-6 max-w-md text-lg text-primary-fixed">Кіріп, тапсырмаларды жалғастырыңыз.</p>
          </div>
          <div className="relative z-10 mt-12 flex justify-center lg:justify-start">
            <div className="w-full max-w-md rounded-[2rem] border border-white/10 bg-white/10 p-8 backdrop-blur">
              <div className="mb-8 rounded-[2rem] bg-white/10 p-6">
                <p className="text-sm font-semibold text-primary-fixed">Жеке кабинет</p>
                <p className="mt-2 text-2xl font-black leading-tight">Тапсырмалар мен нәтижелер бір жерде.</p>
              </div>
              <div className="grid grid-cols-3 gap-3 text-center text-sm font-bold">
                <div className="rounded-2xl bg-white/10 px-4 py-5">Тапсырма</div>
                <div className="rounded-2xl bg-white/10 px-4 py-5">Нәтиже</div>
                <div className="rounded-2xl bg-white/10 px-4 py-5">Даму</div>
              </div>
            </div>
          </div>
        </section>
        <section className="flex items-center bg-white p-8 lg:col-span-5 lg:p-16">
          <div className="mx-auto w-full max-w-md">
            <div className="mb-8 flex items-center justify-between">
              <h2 className="text-3xl font-black text-on-surface">Оқушы</h2>
              <Link className="text-sm font-bold text-primary" href="/admin/login">
                Әкімші
              </Link>
            </div>
            <LoginForm
              redirectTo="/student/dashboard"
              role="student"
              submitLabel="Кіру"
              title=""
            />
            <p className="mt-6 text-center text-sm font-medium text-secondary">
              Аккаунт жоқ па?{" "}
              <Link className="font-bold text-primary" href="/register">
                Тіркелу
              </Link>
            </p>
          </div>
        </section>
      </div>
    </main>
  );
}
