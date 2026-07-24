"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { Bag, Document, Logout, User } from "react-iconly";
import { Container } from "@/components/ui/container";
import { Button } from "@/components/ui/button";
import { useMe } from "@/features/auth/queries";
import { authService } from "@/services/auth";
import { isLoggedIn } from "@/lib/api-client";

export function AccountHubView() {
  const router = useRouter();
  const hasToken = typeof window !== "undefined" && isLoggedIn();
  const { data: me, isLoading } = useMe(hasToken);

  useEffect(() => {
    if (!isLoggedIn()) {
      router.replace("/login?next=/account");
    }
  }, [router]);

  if (!isLoggedIn()) {
    return (
      <Container className="py-16">
        <p className="text-center text-sm text-muted-foreground">در حال هدایت به ورود…</p>
      </Container>
    );
  }

  const logout = async () => {
    await authService.logout();
    window.dispatchEvent(new Event("karzar-auth-change"));
    router.push("/");
  };

  return (
    <Container className="py-8 lg:py-12">
      <h1 className="text-2xl font-bold text-foreground">حساب کاربری</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        {isLoading ? "…" : me?.full_name || me?.phone || "کاربر کارزار"}
      </p>

      <div className="mt-8 grid gap-3 sm:grid-cols-2">
        <HubLink
          href="/account/orders?mode=purchase"
          title="سفارش‌ها"
          desc="پیگیری خریدهای ثبت‌شده"
          Icon={Bag}
        />
        <HubLink
          href="/account/orders?mode=inquiry"
          title="استعلام‌ها"
          desc="درخواست‌های پیش‌فاکتور"
          Icon={Document}
        />
        <HubLink
          href="/account/security"
          title="امنیت حساب"
          desc="تغییر رمز عبور (در صورت داشتن رمز)"
          Icon={User}
        />
      </div>

      <div className="mt-8">
        <Button variant="outline" className="gap-2" onClick={() => void logout()}>
          <Logout set="light" />
          خروج از حساب
        </Button>
      </div>
    </Container>
  );
}

function HubLink({
  href,
  title,
  desc,
  Icon,
}: {
  href: string;
  title: string;
  desc: string;
  Icon: typeof Bag;
}) {
  return (
    <Link
      href={href}
      className="flex items-start gap-3 rounded-xl bg-card p-5 shadow-soft transition-shadow hover:shadow-card"
    >
      <span className="grid h-11 w-11 place-items-center rounded-lg bg-accent text-accent-foreground">
        <Icon set="bold" />
      </span>
      <span>
        <span className="block font-medium text-foreground">{title}</span>
        <span className="mt-0.5 block text-xs text-muted-foreground">{desc}</span>
      </span>
    </Link>
  );
}
