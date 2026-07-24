"use client";

import Image from "next/image";
import Link from "next/link";
import { motion } from "framer-motion";
import { Activity, ChevronLeft, People, ShieldDone, Star, Work } from "react-iconly";
import { Container } from "@/components/ui/container";
import { Button } from "@/components/ui/button";
import { formatNumber } from "@/lib/utils";

const STATS = [
  { value: 12, suffix: "+", label: "سال تجربه", Icon: Activity },
  { value: 8000, suffix: "+", label: "مشتری وفادار", Icon: People },
  { value: 50, suffix: "+", label: "برند معتبر", Icon: Work },
  { value: 100, suffix: "٪", label: "ضمانت اصالت", Icon: ShieldDone },
];

const VALUES = [
  {
    Icon: ShieldDone,
    title: "اصالت و کیفیت",
    desc: "هر کالا با تضمین اصل بودن و مستقیماً از نمایندگی‌های رسمی عرضه می‌شود.",
  },
  {
    Icon: Star,
    title: "تخصص فنی",
    desc: "تیم ما از مهندسان و کارشناسان ابزار تشکیل شده تا بهترین مشاوره را ارائه دهد.",
  },
  {
    Icon: People,
    title: "مشتری‌مداری",
    desc: "پشتیبانی واقعی، پاسخ‌گویی سریع و خدمات پس از فروش حرفه‌ای.",
  },
];

const TIMELINE = [
  { year: "۱۳۹۲", title: "آغاز راه", desc: "شروع فعالیت به‌صورت یک فروشگاه تخصصی ابزار." },
  { year: "۱۳۹۷", title: "توسعه برندها", desc: "همکاری با نمایندگی‌های رسمی برندهای جهانی." },
  { year: "۱۴۰۱", title: "فروشگاه آنلاین", desc: "راه‌اندازی پلتفرم آنلاین کارزار." },
  { year: "۱۴۰۳", title: "مرجع صنعت", desc: "تبدیل‌شدن به یکی از مراجع اصلی ابزار صنعتی." },
];

const fadeUp = {
  hidden: { opacity: 0, y: 28 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5 } },
};

export function AboutView() {
  return (
    <div className="bg-hero-glow">
      {/* Hero */}
      <Container className="py-12 lg:py-20">
        <div className="grid items-center gap-10 lg:grid-cols-2">
          <motion.div initial="hidden" animate="show" variants={fadeUp}>
            <span className="inline-block rounded-full bg-accent px-3 py-1 text-xs font-bold text-primary">
              داستان ما
            </span>
            <h1 className="mt-5 text-3xl font-bold leading-tight text-foreground sm:text-4xl">
              ابزارِ درست، در دستانِ حرفه‌ای‌ها
            </h1>
            <p className="mt-5 max-w-lg text-base leading-8 text-muted-foreground">
              کارزار با هدف ساده‌تر کردن دسترسی صنعتگران ایرانی به ابزار اصیل و
              باکیفیت شکل گرفت. ما باور داریم که یک ابزار خوب، تفاوت میان کار
              معمولی و کار بی‌نقص است.
            </p>
            <Link href="/catalog" className="mt-8 inline-block">
              <Button size="lg" className="gap-2">
                مشاهده محصولات
                <ChevronLeft size="small" set="bold" />
              </Button>
            </Link>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.6 }}
            className="relative aspect-[4/3] overflow-hidden rounded-3xl shadow-elevated"
          >
            <Image
              src="https://images.unsplash.com/photo-1530124566582-a618bc2615dc?w=1200&q=80"
              alt="کارگاه کارزار"
              fill
              priority
              sizes="(max-width: 1024px) 100vw, 50vw"
              className="object-cover"
            />
          </motion.div>
        </div>
      </Container>

      {/* Marketing overview — not live KPIs */}
      <Container>
        <p className="mb-3 text-center text-xs text-muted-foreground">
          نمای کلی برند — آمار رسمی داشبورد یا گزارش سروری نیست
        </p>
        <motion.div
          initial="hidden"
          whileInView="show"
          viewport={{ once: true }}
          variants={{ show: { transition: { staggerChildren: 0.08 } } }}
          className="grid grid-cols-2 gap-4 lg:grid-cols-4"
        >
          {STATS.map(({ value, suffix, label, Icon }) => (
            <motion.div
              key={label}
              variants={fadeUp}
              className="rounded-2xl bg-card p-6 text-center shadow-soft"
            >
              <span className="mx-auto grid h-12 w-12 place-items-center rounded-xl bg-accent text-primary">
                <Icon set="bold" primaryColor="#C22026" />
              </span>
              <p className="mt-4 text-2xl font-bold text-foreground tnum">
                {formatNumber(value)}
                {suffix}
              </p>
              <p className="mt-1 text-sm text-muted-foreground">{label}</p>
            </motion.div>
          ))}
        </motion.div>
      </Container>

      {/* Values */}
      <Container className="py-16 lg:py-24">
        <div className="mb-10 text-center">
          <h2 className="text-2xl font-bold text-foreground sm:text-3xl">ارزش‌های ما</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            آنچه کارزار را متفاوت می‌کند
          </p>
        </div>
        <div className="grid gap-5 md:grid-cols-3">
          {VALUES.map(({ Icon, title, desc }, i) => (
            <motion.div
              key={title}
              initial={{ opacity: 0, y: 28 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-60px" }}
              transition={{ duration: 0.45, delay: i * 0.1 }}
              className="rounded-2xl bg-card p-7 shadow-soft"
            >
              <span className="grid h-14 w-14 place-items-center rounded-2xl bg-primary text-primary-foreground shadow-primary-glow">
                <Icon set="bold" />
              </span>
              <h3 className="mt-5 text-lg font-bold text-foreground">{title}</h3>
              <p className="mt-2 text-sm leading-7 text-muted-foreground">{desc}</p>
            </motion.div>
          ))}
        </div>
      </Container>

      {/* Timeline */}
      <Container className="pb-20">
        <div className="mb-10 text-center">
          <h2 className="text-2xl font-bold text-foreground sm:text-3xl">مسیر ما</h2>
        </div>
        <div className="relative mx-auto max-w-2xl">
          <div className="absolute bottom-0 end-[7px] top-2 w-0.5 bg-border" />
          <div className="space-y-8">
            {TIMELINE.map((item, i) => (
              <motion.div
                key={item.year}
                initial={{ opacity: 0, x: -24 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true, margin: "-60px" }}
                transition={{ duration: 0.45, delay: i * 0.08 }}
                className="relative pe-8"
              >
                <span className="absolute end-0 top-1.5 h-4 w-4 rounded-full bg-primary ring-4 ring-accent" />
                <span className="text-sm font-bold text-primary tnum">{item.year}</span>
                <h3 className="mt-1 text-base font-bold text-foreground">{item.title}</h3>
                <p className="mt-1 text-sm leading-7 text-muted-foreground">{item.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </Container>

      {/* CTA */}
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
            آماده‌اید بهترین ابزار را انتخاب کنید؟
          </h2>
          <p className="relative mx-auto mt-3 max-w-md text-sm text-white/85">
            همین حالا فروشگاه کارزار را مرور کنید و با خیال راحت خرید کنید.
          </p>
          <Link href="/catalog" className="relative mt-7 inline-block">
            <Button variant="soft" size="lg" className="gap-2">
              ورود به فروشگاه
              <ChevronLeft size="small" set="bold" />
            </Button>
          </Link>
        </motion.div>
      </Container>
    </div>
  );
}
