"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { ChevronLeft } from "react-iconly";
import { Logo } from "@/components/layout/logo";
import { Container } from "@/components/ui/container";
import { Button } from "@/components/ui/button";

const fadeUp = {
  hidden: { opacity: 0, y: 28 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5 } },
};

const BENEFITS = [
  {
    title: "اصالت و کیفیت",
    desc: "محصولات از نمایندگی‌ها و تأمین‌کنندگان معتبر تهیه می‌شوند و اصالت کالا در فرایند تأمین و فروش بررسی می‌شود.",
  },
  {
    title: "مشاوره تخصصی",
    desc: "برای انتخاب ابزار، تجهیزات کارگاهی و طراحی یا توسعه خط تولید می‌توانید از راهنمایی فنی کارزار استفاده کنید.",
  },
  {
    title: "تأمین تجهیزات کارگاهی",
    desc: "نیاز کارگاه، پروژه یا مجموعه تولیدی خود را اعلام کنید تا گزینه‌های مناسب از نظر مشخصات، زمان تأمین و شرایط خرید بررسی شوند.",
  },
  {
    title: "خرید سازمانی",
    desc: "کسب‌وکارها و مجموعه‌های صنعتی می‌توانند برای خرید سازمانی، استعلام و پیگیری متمرکز درخواست همکاری ثبت کنند.",
  },
  {
    title: "پیش‌فاکتور رسمی",
    desc: "امکان ثبت اقلام و دریافت پیش‌فاکتور رسمی، مسیر استعلام و خرید را برای واحدهای فنی و مالی شفاف‌تر می‌کند.",
  },
  {
    title: "ارسال سراسری",
    desc: "سفارش‌ها با امکان ارسال به سراسر کشور و پیگیری فرایند تأمین و تحویل ارائه می‌شوند.",
  },
];

export function AboutView() {
  return (
    <div className="bg-hero-glow">
      <Container className="py-12 lg:py-20">
        <div className="grid items-center gap-10 lg:grid-cols-2">
          <motion.div initial="hidden" animate="show" variants={fadeUp}>
            <span className="inline-block rounded-full bg-accent px-3 py-1 text-xs font-bold text-primary">
              درباره ما
            </span>
            <h1 className="mt-5 text-3xl font-bold leading-tight text-foreground sm:text-4xl">
              ابزار درست، در دستان حرفه‌ای‌ها
            </h1>
            <p className="mt-5 max-w-lg text-base leading-8 text-muted-foreground">
              کارزار فروشگاهی تخصصی برای انتخاب و تأمین ابزارآلات صنعتی، تراشکاری و اندازه‌گیری است.
              هدف ما این است که مسیر پیدا کردن ابزار مناسب، بررسی مشخصات، دریافت مشاوره و خرید برای
              صنعتگران، کارگاه‌ها و مجموعه‌های تولیدی روشن، دقیق و قابل‌اعتماد باشد.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link href="/catalog">
                <Button size="lg" className="gap-2">
                  مشاهده محصولات
                  <ChevronLeft size="small" set="bold" />
                </Button>
              </Link>
              <Link href="/contact">
                <Button size="lg" variant="soft" className="gap-2">
                  دریافت مشاوره
                </Button>
              </Link>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.6 }}
            className="flex items-center justify-center lg:justify-end"
          >
            <Logo variant="slogan" height={72} tone="brand" className="max-w-[min(100%,320px)]" />
          </motion.div>
        </div>
      </Container>

      <Container className="pb-12 lg:pb-16">
        <motion.div
          initial="hidden"
          whileInView="show"
          viewport={{ once: true }}
          variants={fadeUp}
          className="max-w-3xl"
        >
          <h2 className="text-2xl font-bold text-foreground sm:text-3xl">
            انتخاب فنی، نه صرفاً خرید کالا
          </h2>
          <p className="mt-4 text-base leading-8 text-muted-foreground">
            در خرید ابزار صنعتی، نام محصول به‌تنهایی کافی نیست. نوع عملیات، جنس قطعه، دستگاه، دقت
            موردنیاز و شرایط کار تعیین می‌کند کدام انتخاب مناسب است. کارزار در کنار تنوع محصول،
            اطلاعات فنی و امکان دریافت مشاوره را فراهم می‌کند تا انتخاب بر اساس نیاز واقعی انجام شود.
          </p>
        </motion.div>
      </Container>

      <Container className="pb-16 lg:pb-24">
        <div className="mb-10">
          <h2 className="text-2xl font-bold text-foreground sm:text-3xl">آنچه از کارزار دریافت می‌کنید</h2>
        </div>
        <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
          {BENEFITS.map((item, i) => (
            <motion.div
              key={item.title}
              initial={{ opacity: 0, y: 28 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-60px" }}
              transition={{ duration: 0.45, delay: i * 0.06 }}
              className="rounded-2xl bg-card p-7 shadow-soft"
            >
              <h3 className="text-lg font-bold text-foreground">{item.title}</h3>
              <p className="mt-2 text-sm leading-7 text-muted-foreground">{item.desc}</p>
            </motion.div>
          ))}
        </div>
      </Container>

      <Container className="pb-20">
        <motion.div
          initial={{ opacity: 0, y: 28 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="relative overflow-hidden rounded-3xl bg-primary p-10 text-center text-primary-foreground shadow-primary-glow sm:p-16"
        >
          <div className="bg-hero-glow absolute inset-0 opacity-30" />
          <h2 className="relative text-2xl font-bold sm:text-3xl">
            برای تصمیم‌های فنی شما کنار کاریم
          </h2>
          <p className="relative mx-auto mt-3 max-w-2xl text-sm leading-7 text-white/85">
            چه به‌دنبال جایگزینی یک ابزار مصرفی باشید، چه برای تجهیز کارگاه یا توسعه تولید
            برنامه‌ریزی کنید، کارزار مسیر بررسی، انتخاب و تأمین را یکپارچه می‌کند.
          </p>
          <div className="relative mt-7 flex flex-wrap items-center justify-center gap-3">
            <Link href="/catalog">
              <Button variant="soft" size="lg" className="gap-2">
                ورود به فروشگاه
                <ChevronLeft size="small" set="bold" />
              </Button>
            </Link>
            <Link href="/contact">
              <Button
                size="lg"
                variant="outline"
                className="border-white/40 bg-transparent text-white hover:bg-white/10"
              >
                تماس با ما
              </Button>
            </Link>
          </div>
        </motion.div>
      </Container>
    </div>
  );
}
