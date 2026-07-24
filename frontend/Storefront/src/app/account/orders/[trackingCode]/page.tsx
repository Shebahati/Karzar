import { OrderDetailView } from "@/components/account/order-detail-view";

export default async function AccountOrderDetailPage({
  params,
}: {
  params: Promise<{ trackingCode: string }>;
}) {
  const { trackingCode } = await params;
  return <OrderDetailView trackingCode={decodeURIComponent(trackingCode)} />;
}
