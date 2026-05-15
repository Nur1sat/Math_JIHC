"use client";

import Link from "next/link";

import { RegisterForm } from "@/components/register-form";
import { BrandIdentity } from "@/components/ui";
import { useGuestRoute } from "@/lib/session";

export default function StudentRegisterPage() {
  const { ready } = useGuestRoute();

  if (!ready) {
    return null;
  }

  return (
    <main className="bg-auth-gradient flex min-h-screen items-center justify-center px-4 py-8 md:px-8">
      <div className="grid w-full max-w-6xl overflow-hidden rounded-[2rem] bg-surface-container-lowest shadow-[0_20px_60px_rgba(46,108,0,0.12)] lg:grid-cols-12">
        <section className="flex min-h-[360px] flex-col justify-between bg-primary p-8 text-on-primary lg:col-span-6 lg:min-h-[720px] lg:p-12">
          <BrandIdentity light />
          <div>
            <h1 className="max-w-xl text-4xl font-black leading-tight md:text-5xl">
              Оқушы ретінде тіркелу
            </h1>
            <p className="mt-5 max-w-md text-lg text-primary-fixed">
              Жеке кабинет ашып, тапсырмаларды бірден орындаңыз.
            </p>
          </div>
          <div className="grid grid-cols-3 gap-3 text-center text-sm font-bold">
            <div className="rounded-2xl bg-white/10 px-4 py-5">Кіру</div>
            <div className="rounded-2xl bg-white/10 px-4 py-5">Шешу</div>
            <div className="rounded-2xl bg-white/10 px-4 py-5">Нәтиже</div>
          </div>
        </section>
        <section className="flex items-center bg-white p-8 lg:col-span-6 lg:p-16">
          <div className="mx-auto w-full max-w-md">
            <div className="mb-8 flex items-center justify-between gap-4">
              <h2 className="text-3xl font-black text-on-surface">Тіркелу</h2>
              <Link className="text-sm font-bold text-primary" href="/">
                Кіру
              </Link>
            </div>
            <RegisterForm />
          </div>
        </section>
      </div>
    </main>
  );
}
