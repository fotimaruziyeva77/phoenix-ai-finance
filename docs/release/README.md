# MVP launch — release documentation

Principal engineering and release entry point for **BotForge AI MVP**. These documents are **operational truth** for go-live: they complement but do not replace `docs/deployment/` (build, migrate, tiers).

| Document | Use when |
|----------|----------|
| [RELEASE_READINESS_GATE.md](./RELEASE_READINESS_GATE.md) | **Final production gate** — go/no-go, evidence, risk register, role sign-off |
| [RELEASE_HEALTH_BOARD.md](./RELEASE_HEALTH_BOARD.md) | **Unified regression board** — CI, E2E, load, DB, gate in one report + thresholds + trends |
| [MVP_RELEASE_CHECKLIST.md](./MVP_RELEASE_CHECKLIST.md) | Practical smoke checklist before cutover (use with the gate above) |
| [ARCHITECTURE_MVP.md](./ARCHITECTURE_MVP.md) | Architecture verdict, boundaries, MVP vs future work |
| [ENV_CONFIG_CHECKLIST.md](./ENV_CONFIG_CHECKLIST.md) | Required and feature-gated variables per tier |
| [MIGRATION_AND_PROMOTION_ORDER.md](./MIGRATION_AND_PROMOTION_ORDER.md) | DB migrations vs app deploy order |
| [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) | First-line incidents and common failures |
| [SPRINT12_REGRESSION_VERIFICATION.md](./SPRINT12_REGRESSION_VERIFICATION.md) | Latest recorded regression matrix (Sprint 12) |

**Also use**

- [docs/deployment/RUNBOOK.md](../deployment/RUNBOOK.md) — build, migrate, start, rollback
- [docs/deployment/RELEASE_PROCESS.md](../deployment/RELEASE_PROCESS.md) — staging → production promotion
- [docs/deployment/PRODUCTION_ENV.md](../deployment/PRODUCTION_ENV.md) — full env reference
- [docs/qa/MVP_E2E_VERIFICATION.md](../qa/MVP_E2E_VERIFICATION.md) — automated vs manual verification map
