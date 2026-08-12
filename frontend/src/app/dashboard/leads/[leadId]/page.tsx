import type { Metadata } from "next";

import { LeadDetailPage } from "@/components/dashboard/leads/lead-detail-page";

export const metadata: Metadata = {
  title: "Lead",
};

type Props = {
  params: Promise<{ leadId: string }>;
};

export default async function DashboardLeadDetailPage({ params }: Props) {
  const { leadId } = await params;
  return <LeadDetailPage leadId={leadId} />;
}
