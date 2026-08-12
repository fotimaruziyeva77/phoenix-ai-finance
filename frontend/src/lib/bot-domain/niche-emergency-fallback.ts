/**
 * Last-resort wizard/landing rows if ``GET /api/v1/catalog/niches`` fails.
 * Shape matches :func:`fetchNicheCatalog` — update when backend niches change.
 */
import type { NicheCatalogItemDto } from "@/lib/api/niche-catalog";

export const EMERGENCY_NICHE_CATALOG_ITEMS: NicheCatalogItemDto[] = [
  {
    id: "education",
    display_name: "Education",
    description: "Capture learner intent, program fit, and enrollment readiness.",
    wizard_hint: "Admissions, courses, student support",
    icon_key: "graduation-cap",
    supported_goals: ["support", "sales", "faq", "consulting"],
    onboarding_hints: ["Start with program interest and timeline questions."],
    default_welcome_messages: {},
    visible: true,
  },
  {
    id: "healthcare",
    display_name: "Healthcare / Clinic",
    description: "Qualify appointment requests and route patient inquiries responsibly.",
    wizard_hint: "Appointments, triage, and patient FAQs",
    icon_key: "stethoscope",
    supported_goals: ["support", "sales", "faq", "consulting"],
    onboarding_hints: ["Keep triage language careful; escalate when unsure."],
    default_welcome_messages: {},
    visible: true,
  },
  {
    id: "dev_agency",
    display_name: "Dev / Agency",
    description: "Collect project scope, budget signal, and timeline expectations.",
    wizard_hint: "Project intake, scope, and client comms",
    icon_key: "code",
    supported_goals: ["support", "sales", "faq", "consulting"],
    onboarding_hints: ["Capture scope and budget signal before hand-off."],
    default_welcome_messages: {},
    visible: true,
  },
  {
    id: "services",
    display_name: "Services",
    description: "Capture job type, location, and preferred follow-up for local services.",
    wizard_hint: "Bookings, quotes, and service requests",
    icon_key: "briefcase",
    supported_goals: ["support", "sales", "faq", "consulting"],
    onboarding_hints: ["Ask for service type and service area early."],
    default_welcome_messages: {},
    visible: true,
  },
];
