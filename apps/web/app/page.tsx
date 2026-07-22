import { DashboardShell } from "@/app/shell";
import { StatusBadge } from "@/app/status-badge";
import { getBackendHealth } from "@/lib/api-client";

export default async function Home() {
  const health = await getBackendHealth();

  return (
    <DashboardShell>
      <div className="grid gap-6 py-3">
        <header className="flex flex-col gap-4 border-b border-line pb-5 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase text-signal">Phase 1 Foundation</p>
            <h1 className="mt-2 text-3xl font-semibold text-ink">
              Industrial Maintenance Knowledge Copilot
            </h1>
            <p className="mt-3 max-w-3xl text-base leading-7 text-slate-600">
              A clean foundation for an asset-centered, cited maintenance intelligence platform.
            </p>
          </div>
          <StatusBadge status={health?.status ?? "unknown"} />
        </header>

        <section className="grid gap-4 md:grid-cols-3">
          <div className="rounded border border-line bg-white p-4">
            <h2 className="text-sm font-semibold text-ink">Frontend</h2>
            <p className="mt-2 text-sm text-slate-600">Next.js App Router with TypeScript and Tailwind CSS.</p>
          </div>
          <div className="rounded border border-line bg-white p-4">
            <h2 className="text-sm font-semibold text-ink">Backend</h2>
            <p className="mt-2 text-sm text-slate-600">FastAPI health endpoints and typed settings.</p>
          </div>
          <div className="rounded border border-line bg-white p-4">
            <h2 className="text-sm font-semibold text-ink">Data Services</h2>
            <p className="mt-2 text-sm text-slate-600">PostgreSQL and Qdrant connectivity checks.</p>
          </div>
        </section>
      </div>
    </DashboardShell>
  );
}
