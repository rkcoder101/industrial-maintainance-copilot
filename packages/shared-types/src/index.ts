export type ComponentStatus = "ok" | "degraded" | "down";

export type ComponentHealth = {
  name: string;
  status: ComponentStatus;
  latency_ms?: number | null;
  message?: string | null;
};

export type HealthResponse = {
  status: ComponentStatus;
  service: string;
  version: string;
  checked_at: string;
  components: ComponentHealth[];
};
