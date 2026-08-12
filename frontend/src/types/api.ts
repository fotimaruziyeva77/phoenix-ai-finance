/** Matches FastAPI `GET /api/v1/health` when wired to the real backend. */
export type HealthStatus = {
  status: string;
};
