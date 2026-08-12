import { SuperadminTenantInspect } from "@/components/superadmin/superadmin-tenant-inspect";

type Props = {
  params: Promise<{ userId: string }>;
};

export default async function SuperadminTenantInspectPage({ params }: Props) {
  const { userId } = await params;
  return <SuperadminTenantInspect userId={userId} />;
}
