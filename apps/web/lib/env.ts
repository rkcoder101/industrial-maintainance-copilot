import { z } from "zod";

const serverEnvSchema = z.object({
  API_INTERNAL_BASE_URL: z.string().url().default("http://localhost:8000"),
  NEXT_PUBLIC_API_BASE_URL: z.string().url().default("http://localhost:8000")
});

export const env = serverEnvSchema.parse({
  API_INTERNAL_BASE_URL: process.env.API_INTERNAL_BASE_URL,
  NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL
});
