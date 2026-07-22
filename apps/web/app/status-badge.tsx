import React from "react";

type StatusBadgeProps = {
  status: "ok" | "degraded" | "down" | "unknown";
};

const labels: Record<StatusBadgeProps["status"], string> = {
  ok: "Online",
  degraded: "Degraded",
  down: "Down",
  unknown: "Unknown"
};

const classes: Record<StatusBadgeProps["status"], string> = {
  ok: "border-signal/20 bg-signal/10 text-signal",
  degraded: "border-warning/20 bg-warning/10 text-warning",
  down: "border-red-700/20 bg-red-700/10 text-red-700",
  unknown: "border-line bg-white text-slate-600"
};

export function StatusBadge({ status }: StatusBadgeProps) {
  return (
    <span
      className={`inline-flex min-w-20 items-center justify-center rounded px-2.5 py-1 text-xs font-semibold ${classes[status]}`}
    >
      {labels[status]}
    </span>
  );
}
