"use client";

import { Document, Send, ShieldDone, Wallet } from "react-iconly";

const FEATURES = [
  { Icon: ShieldDone, title: "ضمانت اصالت", desc: "تضمین اصل بودن تمام کالاها" },
  { Icon: Send, title: "ارسال سریع", desc: "ارسال به سراسر کشور" },
  { Icon: Wallet, title: "پرداخت امن", desc: "درگاه بانکی معتبر" },
  { Icon: Document, title: "پیش‌فاکتور آنی", desc: "استعلام و فاکتور رسمی" },
];

export function FeatureStrip() {
  return (
    <div className="no-scrollbar -mx-5 flex gap-3 overflow-x-auto px-5 pb-1 sm:mx-0 sm:grid sm:grid-cols-2 sm:gap-4 sm:overflow-visible sm:px-0 lg:grid-cols-4">
      {FEATURES.map(({ Icon, title, desc }) => (
        <div
          key={title}
          className="flex min-w-[220px] shrink-0 items-center gap-3 rounded-2xl border border-border/60 bg-card p-4 shadow-soft sm:min-w-0"
        >
          <span className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-accent text-primary sm:h-12 sm:w-12">
            <Icon set="bold" primaryColor="#C22026" />
          </span>
          <div>
            <p className="text-sm font-bold text-foreground">{title}</p>
            <p className="text-xs text-muted-foreground">{desc}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
