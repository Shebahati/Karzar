import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Container } from "@/components/ui/container";

export default function NotFound() {
  return (
    <Container className="grid min-h-[60vh] place-items-center py-16">
      <div className="w-full max-w-md rounded-2xl bg-card p-8 text-center shadow-soft">
        <p className="text-sm font-bold text-primary">۴۰۴</p>
        <h1 className="mt-2 text-xl font-bold text-foreground">صفحه پیدا نشد</h1>
        <p className="mt-2 text-sm leading-7 text-muted-foreground">
          آدرس واردشده معتبر نیست یا صفحه حذف شده است.
        </p>
        <div className="mt-6">
          <Link href="/">
            <Button type="button">بازگشت به خانه</Button>
          </Link>
        </div>
      </div>
    </Container>
  );
}
