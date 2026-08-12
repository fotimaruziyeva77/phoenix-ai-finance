import { SuperadminBotDetail } from "@/components/superadmin/superadmin-bot-detail";

type Props = {
  params: Promise<{ botId: string }>;
};

export default async function SuperadminBotPage({ params }: Props) {
  const { botId } = await params;
  return <SuperadminBotDetail botId={botId} />;
}
