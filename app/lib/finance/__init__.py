"""Pure-math finance advisory libraries (no DB, no I/O, no AI).

Every number the product shows an entrepreneur is produced here by deterministic
arithmetic. The LLM layer may *explain* these results but must never compute them —
a wrong credit or tax figure is a real financial loss for the user.

**Localisation divergence (2026-08-12).** The browser mirror
(``frontend/src/lib/finance/engine.ts``) now returns i18n *codes* (``{code, params}``)
instead of finished sentences, so the UI can render uz/ru/en. These Python modules
still emit Uzbek strings in ``*_uz`` fields. The arithmetic in both is identical and
must stay that way; the message-code refactor is the outstanding piece here. Do not
add new Uzbek sentences to this package — emit codes when you touch these paths.

Modules:
    * :mod:`app.lib.finance.sectors` — per-sector economics benchmarks
    * :mod:`app.lib.finance.locations` — city/region legal + cost layer (Toshkent, Navoiy, ...)
    * :mod:`app.lib.finance.programs` — state preferential-loan programs + eligibility matching
    * :mod:`app.lib.finance.banks` — commercial bank business-loan offers
    * :mod:`app.lib.finance.credit_calculator` — annuity / differentiated schedules
    * :mod:`app.lib.finance.tax_calculator` — 2026 tax regimes comparison
    * :mod:`app.lib.finance.business_plan` — break-even, payback, verdict
"""

from __future__ import annotations

DATA_AS_OF = "2026-08-12"
"""Date the bundled reference data (rates, thresholds, programs) was last verified."""

__all__ = ["DATA_AS_OF"]
