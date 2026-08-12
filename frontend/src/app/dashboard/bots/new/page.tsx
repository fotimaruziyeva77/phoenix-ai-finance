import type { Metadata } from "next";

import { CreateBotWizard } from "@/components/dashboard/bots/create-wizard/create-bot-wizard";

export const metadata: Metadata = {
  title: "Create bot",
};

export default function DashboardBotsNewPage() {
  return <CreateBotWizard />;
}
