import type { Metadata } from "next";

import { BotDetailPage } from "@/components/dashboard/bots/bot-detail-page";

export const metadata: Metadata = {
  title: "Bot detail",
};

type Props = {
  params: Promise<{ botId: string }>;
};

export default async function DashboardBotDetailPage({ params }: Props) {
  const { botId } = await params;
  return <BotDetailPage botId={botId} />;
}
