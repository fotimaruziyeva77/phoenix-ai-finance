import { SuperadminUserDetail } from "@/components/superadmin/superadmin-user-detail";

type Props = {
  params: Promise<{ userId: string }>;
};

export default async function SuperadminUserPage({ params }: Props) {
  const { userId } = await params;
  return <SuperadminUserDetail userId={userId} />;
}
