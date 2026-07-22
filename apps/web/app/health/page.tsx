import { DashboardShell } from "@/app/shell";
import { StatusBadge } from "@/app/status-badge";
import { getBackendHealth } from "@/lib/api-client";

export default async function HealthPage() {
  const health = await getBackendHealth();
  const components = health?.components ?? [
    {
      name: "api",
      status: "unknown" as const,
      message: "Backend readiness endpoint is unavailable."
    }
  ];

  return (
    <DashboardShell>
      <div className="grid gap-5 py-3">
        <header className="border-b border-line pb-5">
          <p className="text-sm font-semibold uppercase text-signal">Service Health</p>
          <h1 className="mt-2 text-3xl font-semibold text-ink">Runtime Connectivity</h1>
        </header>

        <section className="rounded border border-line bg-white">
          <div className="grid grid-cols-[1fr_auto] gap-3 border-b border-line px-4 py-3 text-sm font-semibold text-slate-700">
            <span>Component</span>
            <span>Status</span>
          </div>
          <div className="divide-y divide-line">
            <div className="grid grid-cols-[1fr_auto] items-center gap-3 px-4 py-3">
              <div>
                <p className="font-medium text-ink">frontend</p>
                <p className="text-sm text-slate-600">Next.js page rendered successfully.</p>
              </div>
              <StatusBadge status="ok" />
            </div>
            {components.map((component) => (
              <div className="grid grid-cols-[1fr_auto] items-center gap-3 px-4 py-3" key={component.name}>
                <div>
                  <p className="font-medium text-ink">{component.name}</p>
                  <p className="text-sm text-slate-600">{component.message ?? "No message reported."}</p>
                </div>
                <StatusBadge status={component.status} />
              </div>
            ))}
          </div>
        </section>
      </div>
    </DashboardShell>
  );
}
