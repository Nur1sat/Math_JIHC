"use client";

import Link from "next/link";

import { clearSession, useSession } from "@/lib/session";
import { BrandIdentity, MaterialIcon, ShellFooter, cn } from "@/components/ui";

const items = [
  { href: "/admin/dashboard", label: "Dashboard", icon: "dashboard", key: "dashboard" },
  { href: "/admin/tasks", label: "Tasks", icon: "quiz", key: "tasks" }
];

export function AdminShell({
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
        <div className="px-4">
          <Link
            className="flex w-full items-center justify-center gap-2 rounded-full bg-primary py-3 font-bold text-on-primary shadow-lg shadow-primary/20 transition-colors hover:bg-primary-container"
            href="/admin/tasks"
          >
            <MaterialIcon icon="add" />
            <span>Add Task</span>
          </Link>
        </div>
      </aside>
      <main className="min-h-screen md:ml-64">
        <header className="fixed left-0 right-0 top-0 z-30 bg-white/80 px-6 py-3 shadow-sm backdrop-blur-xl md:left-64">
          <div className="mx-auto flex w-full max-w-screen-2xl items-center justify-between">
            <div className="flex items-center gap-8">
              <BrandIdentity compact />
            </div>
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-3 border-l border-slate-200 pl-4">
                <div className="hidden text-right sm:block">
                  <p className="text-sm font-bold leading-none">
                    {session?.user.fullName ?? "Admin User"}
                  </p>
                  <p className="text-[10px] font-semibold tracking-tight text-green-600">
                    ADMINISTRATOR
                  </p>
                </div>
                <img
                  alt="User Profile Avatar"
                  className="h-10 w-10 rounded-full border-2 border-primary-container object-cover"
                  src={
                    session?.user.avatarUrl ??
                    "https://lh3.googleusercontent.com/aida-public/AB6AXuCh_dbyTMpXmJS8SdHrj8vz0jeXzqGLv9JzwWeI2reYn55y-_9XZEr8NgkbvR54Slk4k0UQshs8kIKDNmDNt2bFuRQg-QcGP595AcErsnVNN4jD7QqL5Ypoi3El-CWlw3apz3Q5f0X-IDIxwKobLWeSDADA8Zh_zN1EJ6PUHslsqOjTrrKIU0LiVImiRVtXxckcfDxGkNRZehEK2qrMt-bR7JFsjTRqi-SW_v0I6Y0hBTYS8GGb6H-Xi09NNTlQQZ78eejzw4GP33W4"
                  }
                />
                <button
                  className="rounded-full bg-slate-100 px-3 py-2 text-xs font-semibold text-secondary transition-colors hover:bg-slate-200"
                  onClick={() => {
                    clearSession();
                    window.location.href = "/admin/login";
                  }}
                  type="button"
                >
                  Logout
                </button>
              </div>
            </div>
          </div>
        </header>
        <div className="pt-20">{children}</div>
        <ShellFooter />
      </main>
    </div>
  );
}
