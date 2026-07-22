import Link from "next/link";
import type { ReactNode } from "react";

const navigation = [
  "Overview",
  "Equipment",
  "Documents",
  "Recurring Failures",
  "Compliance",
  "Knowledge Graph",
  "Evaluation",
  "Settings"
];

export function DashboardShell({ children }: { children: ReactNode }) {
  return (
    <main className="mx-auto flex min-h-screen w-full max-w-7xl gap-0 px-4 py-4 sm:px-6 lg:px-8">
      <aside className="hidden w-64 shrink-0 border-r border-line pr-5 lg:block">
        <Link className="block py-3 text-sm font-semibold uppercase text-signal" href="/">
          IMKC
        </Link>
        <nav className="mt-4 flex flex-col gap-1">
          {navigation.map((item) => (
            <span
              className="rounded px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-white"
              key={item}
            >
              {item}
            </span>
          ))}
        </nav>
      </aside>
      <section className="min-w-0 flex-1 lg:pl-6">{children}</section>
    </main>
  );
}
