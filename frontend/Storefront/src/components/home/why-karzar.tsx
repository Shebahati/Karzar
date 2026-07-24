"use client";

import { Chart, Send, ShieldDone, TwoUsers } from "react-iconly";

const SERVICES = [
  {
    Icon: ShieldDone,
    title: "ضمانت اصالت کالا",
    desc: "تمام محصولات مستقیماً از نمایندگی‌های رسمی عرضه می‌شوند.",
  },
  {
    Icon: Chart,
    title: "قیمت‌گذاری B2B",
    desc: "تخفیف پلکانی برای خریدهای سازمانی با فاکتور رسمی.",
  },
  {
    Icon: Send,
    title: "ارسال سریع",
    desc: "بسته‌بندی استاندارد و ارسال مطمئن به سراسر کشور.",
  },
  {
    Icon: TwoUsers,
    title: "مشاوره تخصصی",
    desc: "انتخاب درست ابزار متناسب با نیاز شما.",
  },
];

export function WhyKarzar() {
  return (
    <section className="overflow-hidden rounded-3xl border border-border/60 bg-gradient-to-b from-card to-secondary/40 p-6 sm:p-10">
      <div className="mb-8 text-center">
        <span className="inline-block rounded-full bg-accent px-3 py-1 text-xs font-bold text-primary">
          چرا کارزار؟
        </span>
        <h2 className="mt-4 text-xl font-bold text-foreground sm:text-3xl">
          تجربه حرفه‌ای خرید ابزار صنعتی
        </h2>
        <p className="mx-auto mt-2 max-w-md text-sm text-muted-foreground">
          خدماتی که خرید شما را مطمئن، سریع و به‌صرفه می‌کند
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {SERVICES.map(({ Icon, title, desc }) => (
          <article
            key={title}
            className="rounded-2xl border border-border/50 bg-card/90 p-5 shadow-soft sm:p-6"
          >
            <span className="grid h-14 w-14 place-items-center rounded-2xl bg-primary text-primary-foreground">
              <Icon set="bold" size="large" />
            </span>
            <h3 className="mt-4 text-base font-bold text-foreground sm:text-lg">{title}</h3>
            <p className="mt-2 text-sm leading-7 text-muted-foreground">{desc}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
