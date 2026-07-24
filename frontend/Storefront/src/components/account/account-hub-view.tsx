"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo } from "react";
import {
  Bag,
  Document,
  Location,
  Lock,
  Logout,
  Wallet,
} from "react-iconly";
import { Container } from "@/components/ui/container";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useMe } from "@/features/auth/queries";
import { useMyOrders } from "@/features/orders/queries";
import { authService } from "@/services/auth";
import { isLoggedIn } from "@/lib/api-client";
import { cn, formatToman, toPersianDigits } from "@/lib/utils";

function initialOf(name?: string | null, phone?: string | null): string {
  const src = (name || phone || "ک").trim();
  return src.charAt(0);
}

export function AccountHubView() {
  const router = useRouter();
  const hasToken = typeof window !== "undefined" && isLoggedIn();
  const { data: me, isLoading } = useMe(hasToken);
  const { data: ordersData, isPending: ordersPending } = useMyOrders({ limit: 5 });

  useEffect(() => {
    if (!isLoggedIn()) {
      router.replace("/login?next=/account");
    }
  }, [router]);

  const recent = useMemo(() => ordersData?.data.slice(0, 3) ?? [], [ordersData]);
  const displayName = me?.full_name || "کاربر کارزار";
  const phone = me?.phone;

  if (!isLoggedIn()) {
    return (
      <Container className="py-16">
        <p className="text-center text-sm text-steel">در حال هدایت به ورود…</p>
      </Container>
    );
  }

  const logout = async () => {
    await authService.logout();
    window.dispatchEvent(new Event("karzar-auth-change"));
    router.push("/");
  };

  const cards = [
    {
      href: "/account/orders?mode=purchase",
      title: "سفارش‌ها",
      desc: "پیگیری خریدهای ثبت‌شده",
      Icon: Bag,
    },
    {
      href: "/account/orders?mode=inquiry",
      title: "استعلام‌ها",
      desc: "درخواست‌های پیش‌فاکتور",
      Icon: Document,
    },
    {
      href: "/account/invoices",
      title: "فاکتورها",
      desc: "دانلود فاکتور و پیش‌فاکتور",
      Icon: Document,
    },
    {
      href: "/account/payments",
      title: "پرداخت‌ها",
      desc: "وضعیت پرداخت سفارش‌ها",
      Icon: Wallet,
    },
    {
      href: "/account/addresses",
      title: "آدرس‌ها",
      desc: "دفترچه آدرس ارسال",
      Icon: Location,
    },
    {
      href: "/account/security",
      title: "امنیت حساب",
      desc: "تغییر رمز عبور",
      Icon: Lock,
    },
  ] as const;

  return (
    <Container className="py-8 lg:py-12">
      <section className="relative overflow-hidden rounded-3xl border border-border/40 bg-card p-6 shadow-soft sm:p-8">
        <div
          className="pointer-events-none absolute inset-0 opacity-[0.07]"
          style={{
            background:
              "radial-gradient(ellipse at 100% 0%, #C22026 0%, transparent 55%), radial-gradient(ellipse at 0% 100%, #5E5F5E 0%, transparent 50%)",
          }}
        />
        <div className="relative flex flex-wrap items-center gap-4">
          <div className="grid h-16 w-16 place-items-center rounded-2xl bg-primary text-xl font-bold text-primary-foreground shadow-primary-glow">
            {isLoading ? "…" : initialOf(me?.full_name, me?.phone)}
          </div>
          <div className="min-w-0 flex-1">
            <h1 className="truncate text-2xl font-bold text-foreground">
              {isLoading ? "…" : displayName}
            </h1>
            {phone ? (
              <p className="mt-1 text-sm text-steel tnum">{toPersianDigits(phone)}</p>
            ) : (
              <p className="mt-1 text-sm text-steel">حساب کاربری کارزار</p>
            )}
          </div>
          <Button variant="outline" className="gap-2" onClick={() => void logout()}>
            <Logout set="light" />
            خروج
          </Button>
        </div>
      </section>

      <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {cards.map(({ href, title, desc, Icon }) => (
          <Link
            key={href}
            href={href}
            className="group flex items-start gap-3 rounded-2xl border border-border/40 bg-card p-5 shadow-soft transition-all hover:-translate-y-0.5 hover:border-steel/30 hover:shadow-glass"
          >
            <span className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-secondary text-steel transition-colors group-hover:bg-accent group-hover:text-primary">
              <Icon set="bold" />
            </span>
            <span>
              <span className="block font-bold text-foreground">{title}</span>
              <span className="mt-0.5 block text-xs leading-5 text-steel">{desc}</span>
            </span>
          </Link>
        ))}
      </div>

      <section className="mt-8">
        <div className="mb-3 flex items-center justify-between gap-3">
          <h2 className="text-base font-bold text-foreground">سفارش‌های اخیر</h2>
          <Link
            href="/account/orders?mode=purchase"
            className="text-xs font-bold text-primary"
          >
            مشاهده همه
          </Link>
        </div>

        {ordersPending ? (
          <div className="space-y-2">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-16 w-full rounded-2xl" />
            ))}
          </div>
        ) : recent.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-border/60 bg-card/60 px-5 py-10 text-center">
            <p className="text-sm text-steel">هنوز سفارشی ثبت نشده است.</p>
            <Link href="/catalog" className="mt-3 inline-block text-sm font-bold text-primary">
              رفتن به فروشگاه
            </Link>
          </div>
        ) : (
          <ul className="space-y-2">
            {recent.map((order) => (
              <li key={order.id}>
                <Link
                  href={`/account/orders/${order.tracking_code}`}
                  className={cn(
                    "flex flex-wrap items-center justify-between gap-2 rounded-2xl border border-border/40 bg-card px-4 py-3.5 shadow-soft transition-shadow hover:shadow-card",
                  )}
                >
                  <span>
                    <span className="block text-sm font-bold text-foreground tnum">
                      {toPersianDigits(order.tracking_code)}
                    </span>
                    <span className="mt-0.5 block text-[11px] text-steel">
                      {order.mode === "inquiry" ? "استعلام" : "خرید"} ·{" "}
                      {order.status_label}
                    </span>
                  </span>
                  <span className="text-xs font-bold text-steel">
                    {order.estimated_total
                      ? formatToman(order.estimated_total)
                      : toPersianDigits(order.created_at.slice(0, 10))}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </Container>
  );
}
