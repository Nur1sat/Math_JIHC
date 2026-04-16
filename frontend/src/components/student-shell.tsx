"use client";

import Link from "next/link";

import { clearSession, useSession } from "@/lib/session";
import { BrandIdentity, MaterialIcon, ShellFooter, cn } from "@/components/ui";

const items = [
  { href: "/student/dashboard", label: "Dashboard", icon: "dashboard", key: "dashboard" },
  { href: "/student/dashboard#tasks", label: "Tasks", icon: "quiz", key: "tasks" }
];

export function StudentShell({
  active,
  children
}: {
  active: string;
  children: React.ReactNode;
}) {
  const session = useSession();

  return (
    <div className="min-h-screen bg-background text-on-background">
      <aside className="fixed left-0 top-0 hidden h-screen w-64 flex-col space-y-2 bg-slate-50 py-4 md:flex">
        <div className="mb-8 px-6">
          <BrandIdentity compact />
        </div>
        <nav className="flex-1 space-y-1 px-2">
          {items.map((item) => {
            const isActive = item.key === active;
            return (
              <Link
                className={cn(
                  "mx-2 flex items-center gap-3 rounded-xl px-4 py-3 transition-transform hover:translate-x-1",
                  isActive
                    ? "bg-green-100 font-bold text-green-800"
                    : "text-slate-600 hover:bg-slate-200/50"
                )}
                href={item.href}
                key={item.key}
              >
                <MaterialIcon icon={item.icon} />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>
      </aside>
      <main className="min-h-screen md:ml-64">
        <header className="fixed left-0 right-0 top-0 z-30 bg-white/80 px-6 py-3 shadow-sm backdrop-blur-xl md:left-64">
          <div className="mx-auto flex w-full max-w-screen-2xl items-center justify-between">
            <div className="flex flex-1 items-center gap-4">
              <BrandIdentity compact />
            </div>
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-3">
                <div className="hidden text-right sm:block">
                  <span className="block text-sm font-medium text-slate-800">
                    {session?.user.fullName ?? "Student"}
                  </span>
                  <span className="block text-xs text-secondary">
                    {session?.user.gradeLabel ?? "Student"}
                  </span>
                </div>
                <img
                  alt="User Profile Avatar"
                  className="h-10 w-10 rounded-full border-2 border-primary-container object-cover"
                  src={
                    session?.user.avatarUrl ??
                    "https://lh3.googleusercontent.com/aida-public/AB6AXuBZm0J70UMexkn1mPztZFL5tMZwysV2ebpIFbUJdPC0rJvJC2XlmjQVnPUZ00IqwkoXsPQBFMACLYf8Z7CLgXwZhpGVqUsNjBiIUvud7h-7J0JK9oxVx58YXS6Ed9-4L8x9lOtV3aw2IbDbhbvs3ePFsi6zlJw-tlhA-Tp0pguDkyLF0pD2BLHTEATbHRmWgOtODqURsIHfsF4l4vZZAiQYdGK3SC4trbQh5EZw3_Yx_E_WYkfdY5nG3KBajb52LB162B3U8nwjrM65"
                  }
                />
                <button
                  className="rounded-full bg-slate-100 px-3 py-2 text-xs font-semibold text-secondary transition-colors hover:bg-slate-200"
                  onClick={() => {
                    clearSession();
                    window.location.href = "/";
                  }}
                  type="button"
                >
                  Logout
                </button>
              </div>
            </div>
          </div>
        </header>
        <div className="pt-24">{children}</div>
        <ShellFooter />
      </main>
    </div>
  );
}
