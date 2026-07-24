import { Container } from "@/components/ui/container";
import { Skeleton } from "@/components/ui/skeleton";

export default function GlobalLoading() {
  return (
    <Container className="space-y-6 py-10">
      <Skeleton className="h-10 w-48" />
      <Skeleton className="h-40 w-full" />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Skeleton className="h-48 w-full" />
        <Skeleton className="h-48 w-full" />
        <Skeleton className="h-48 w-full" />
      </div>
    </Container>
  );
}
