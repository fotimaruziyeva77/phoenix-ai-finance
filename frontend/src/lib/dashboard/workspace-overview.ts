/**
 * Workspace snapshot for the dashboard overview.
 * Replace with real API calls (e.g. list bots, leads, integrations) when endpoints exist.
 */
export type WorkspaceOverviewState = {
  /** True when at least one bot exists in the workspace. */
  hasBots: boolean;
};

/**
 * Current implementation: no dashboard aggregation API wired yet — empty-first UX.
 */
export function getWorkspaceOverviewState(): WorkspaceOverviewState {
  return { hasBots: false };
}
