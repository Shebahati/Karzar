import { Suspense } from "react";
import { MyOrdersView } from "@/components/account/my-orders-view";

export default function MyOrdersPage() {
  return (
    <Suspense fallback={null}>
      <MyOrdersView />
    </Suspense>
  );
}
