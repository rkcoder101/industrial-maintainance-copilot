import type { HealthResponse } from "@maintenance-copilot/shared-types";
import { env } from "@/lib/env";

export async function getBackendHealth(): Promise<HealthResponse | null> {
  try {
    const response = await fetch(`${env.API_INTERNAL_BASE_URL}/api/v1/health/ready`, {
      cache: "no-store"
    });
    if (!response.ok) {
      return null;
    }
    return (await response.json()) as HealthResponse;
  } catch {
    return null;
  }
}
