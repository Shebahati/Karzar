"use client";

import {
  cloneElement,
  useCallback,
  useEffect,
  useId,
  useRef,
  useState,
  type ReactElement,
} from "react";
import { createPortal } from "react-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { AnimatePresence, motion } from "framer-motion";
import {
  Call,
  Chart,
  CloseSquare,
  Document,
  Setting,
  TickSquare,
  TwoUsers,
} from "react-iconly";
import Link from "next/link";
import { z } from "zod";
import { useSubmitContact } from "@/features/checkout/queries";
import { phoneSchema } from "@/lib/validation";
import { STORE_PHONE_DISPLAY, STORE_PHONE_E164 } from "@/lib/store-location";
import { cn } from "@/lib/utils";
import { useFocusTrap } from "@/lib/use-focus-trap";
import { useMotionSafe } from "@/lib/use-motion-safe";

const LG_MQ = "(min-width: 1024px)";

const AUTO_ADVANCE_MS = 5500;
const FORM_IDLE_RESUME_MS = 2200;

const leadSchema = z.object({
  full_name: z.string().min(2, "نام و نام خانوادگی را کامل وارد کنید."),
  phone: phoneSchema,
  message: z.string().min(8, "کمی بیشتر توضیح دهید تا دقیق‌تر راهنمایی کنیم."),
});
type LeadValues = z.input<typeof leadSchema>;

type CardId = "proforma" | "supply" | "b2b" | "consult";

const CAPABILITIES: Array<{
  id: CardId;
  index: string;
  Icon: typeof Document;
  title: string;
  teaser: string;
  accent?: boolean;
}> = [
  {
    id: "proforma",
    index: "۰۱",
    Icon: Document,
    title: "پیش‌فاکتور رسمی، همان لحظه",
    teaser: "سبد را بچینید؛ PDF قابل استناد را فوری دریافت کنید",
    accent: true,
  },
  {
    id: "supply",
    index: "۰۲",
    Icon: Setting,
    title: "تأمین تجهیزات کارگاهی",
    teaser: "نیاز خط تولید را بسپارید؛ ما منبع‌یابی می‌کنیم",
  },
  {
    id: "b2b",
    index: "۰۳",
    Icon: Chart,
    title: "خرید سازمانی آنلاین",
    teaser: "اکانت همکاری با قیمت و شرایط ویژه کسب‌وکار",
  },
  {
    id: "consult",
    index: "۰۴",
    Icon: TwoUsers,
    title: "مشاوره تخصصی رایگان",
    teaser: "انتخاب ابزار، تراشکاری و طراحی مسیر کارگاه",
    accent: true,
  },
];

const CARD_IDS = CAPABILITIES.map((c) => c.id);

/** High-contrast controls for dark surfaces — light fields, bright labels. */
const darkLabel = "mb-1.5 block text-[13px] font-bold text-white";
const darkInput =
  "h-12 w-full rounded-xl bg-white px-4 text-base font-medium text-[#1a1a1a] outline-none ring-0 placeholder:text-[#5E5F5E]/70 focus:ring-2 focus:ring-[#D02327]/45";
const darkTextarea =
  "w-full rounded-xl bg-white p-4 text-base font-medium text-[#1a1a1a] outline-none placeholder:text-[#5E5F5E]/70 focus:ring-2 focus:ring-[#D02327]/45";

function isFormControl(el: EventTarget | null): boolean {
  if (!(el instanceof HTMLElement)) return false;
  const tag = el.tagName;
  return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || tag === "BUTTON";
}

function DarkField({
  label,
  error,
  children,
}: {
  label: string;
  error?: string;
  children: ReactElement<{ id?: string }>;
}) {
  const autoId = useId();
  const id = children.props.id ?? autoId;

  return (
    <label className="block" htmlFor={id}>
      <span className={darkLabel}>{label}</span>
      {cloneElement(children, { id })}
      {error ? (
        <span className="mt-1.5 block text-xs font-bold text-[#ff8b8e]" role="alert">
          {error}
        </span>
      ) : null}
    </label>
  );
}

function LeadForm({
  subject,
  phoneHint,
  cta = "ثبت درخواست",
}: {
  subject: string;
  phoneHint?: boolean;
  cta?: string;
}) {
  const form = useForm<LeadValues>({ resolver: zodResolver(leadSchema) });
  const submit = useSubmitContact();
  const { errors } = form.formState;

  const onSubmit = form.handleSubmit((values) =>
    submit.mutate({
      full_name: values.full_name,
      phone: values.phone,
      subject,
      message: values.message,
    }),
  );

  if (submit.isSuccess) {
    return (
      <div className="flex flex-col items-center gap-3 rounded-2xl bg-white/[0.07] px-5 py-10 text-center">
        <span className="grid h-14 w-14 place-items-center rounded-full bg-[#D02327] text-white shadow-[0_12px_32px_rgba(208,35,39,0.4)]">
          <TickSquare set="bold" />
        </span>
        <p className="text-base font-black text-white">درخواست شما ثبت شد</p>
        <p className="max-w-xs text-sm leading-6 text-white/70">
          کارشناس کارزار در کوتاه‌ترین زمان با شما تماس می‌گیرد.
          {submit.data?.ticket ? (
            <>
              {" "}
              کد پیگیری:{" "}
              <span className="font-black text-white" dir="ltr">
                {submit.data.ticket}
              </span>
            </>
          ) : null}
        </p>
      </div>
    );
  }

  return (
    <form onSubmit={onSubmit} className="space-y-3.5">
      <div className="grid gap-3.5 sm:grid-cols-2">
        <DarkField label="نام و نام خانوادگی" error={errors.full_name?.message}>
          <input
            className={darkInput}
            placeholder="مثلاً محمد احمدی"
            autoComplete="name"
            {...form.register("full_name")}
          />
        </DarkField>
        <DarkField label="شماره موبایل" error={errors.phone?.message}>
          <input
            className={darkInput}
            dir="ltr"
            inputMode="tel"
            autoComplete="tel"
            placeholder="0912xxxxxxx"
            {...form.register("phone")}
          />
        </DarkField>
      </div>
      <DarkField label="شرح نیاز شما" error={errors.message?.message}>
        <textarea
          className={darkTextarea}
          rows={3}
          placeholder="نوع تجهیزات، تعداد تقریبی یا موضوع مشاوره را بنویسید…"
          {...form.register("message")}
        />
      </DarkField>
      <button
        type="submit"
        disabled={submit.isPending}
        className="inline-flex h-12 w-full items-center justify-center rounded-xl bg-[#D02327] text-sm font-black text-white shadow-[0_12px_28px_rgba(208,35,39,0.35)] transition hover:bg-[#b81e23] disabled:opacity-60"
      >
        {submit.isPending ? "در حال ارسال…" : cta}
      </button>
      {phoneHint ? (
        <a
          href={`tel:${STORE_PHONE_E164}`}
          className="flex items-center justify-center gap-2 pt-1 text-sm font-black text-white transition hover:text-[#ffb0b2]"
          dir="ltr"
        >
          <Call size="small" set="bold" primaryColor="#D02327" />
          {STORE_PHONE_DISPLAY}
        </a>
      ) : null}
    </form>
  );
}

function DetailBody({ id }: { id: CardId }) {
  if (id === "proforma") {
    return (
      <div className="space-y-5">
        <p className="text-[15px] leading-8 text-white/80">
          ابزارهای موردنیاز را در فروشگاه به سبد اضافه کنید، سپس{" "}
          <span className="font-black text-white">دریافت پیش‌فاکتور</span> را بزنید و PDF رسمی را
          همان لحظه دانلود کنید — مناسب استعلام، بایگانی حسابداری و خرید سازمانی.
        </p>
        <ul className="grid gap-2 sm:grid-cols-3">
          {["بدون انتظار تلفنی", "PDF رسمی همان لحظه", "آماده برای حسابداری"].map((item) => (
            <li
              key={item}
              className="rounded-xl bg-white/[0.08] px-3 py-3 text-center text-xs font-bold text-white/90"
            >
              {item}
            </li>
          ))}
        </ul>
        <div className="flex flex-wrap gap-2.5 pt-1">
          <Link
            href="/catalog"
            className="inline-flex h-12 items-center justify-center rounded-xl bg-[#D02327] px-6 text-sm font-black text-white shadow-[0_12px_28px_rgba(208,35,39,0.35)] transition hover:bg-[#b81e23]"
          >
            رفتن به فروشگاه
          </Link>
          <Link
            href="/cart"
            className="inline-flex h-12 items-center justify-center rounded-xl bg-white px-6 text-sm font-black text-[#1a1a1a] transition hover:bg-white/90"
          >
            مشاهده سبد خرید
          </Link>
        </div>
      </div>
    );
  }

  if (id === "supply") {
    return (
      <div className="space-y-5">
        <p className="text-[15px] leading-8 text-white/80">
          تجهیزات خط تولید، کارگاه یا پروژه را مشخص کنید — تیم تأمین کارزار منبع‌یابی می‌کند و
          پیشنهاد زمان‌بندی و قیمت را به شما می‌رساند.
        </p>
        <LeadForm subject="تأمین تجهیزات — صفحه اصلی" cta="ارسال درخواست تأمین" />
      </div>
    );
  }

  if (id === "b2b") {
    return (
      <div className="space-y-5">
        <p className="text-[15px] leading-8 text-white/80">
          برای فعال‌سازی اکانت همکاری درخواست بدهید تا حساب شما شرکتی شود و بتوانید با{" "}
          <span className="font-black text-white">قیمت و شرایط سازمانی</span> به‌صورت آنلاین خرید
          ثبت کنید.
        </p>
        <LeadForm subject="درخواست اکانت B2B — صفحه اصلی" phoneHint cta="درخواست اکانت همکاری" />
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <p className="text-[15px] leading-8 text-white/80">
        برای انتخاب ابزار، تراشکاری، طراحی خط تولید یا راه‌اندازی کارگاه، مشاوره تخصصی رایگان
        دریافت کنید — بدون تعهد خرید.
      </p>
      <LeadForm subject="مشاوره تخصصی رایگان — صفحه اصلی" phoneHint cta="رزرو مشاوره رایگان" />
    </div>
  );
}

function PanelChrome({ id }: { id: CardId }) {
  const active = CAPABILITIES.find((c) => c.id === id)!;
  return (
    <>
      <div className="mb-5 flex items-center gap-3">
        <span className="grid h-12 w-12 place-items-center rounded-2xl bg-[#D02327] text-white shadow-[0_12px_28px_rgba(208,35,39,0.4)]">
          <active.Icon set="bold" />
        </span>
        <div>
          <p className="text-[11px] font-bold tracking-normal text-white/45">
            {active.index} · قابلیت کارزار
          </p>
          <h3 className="text-xl font-black leading-[1.45] tracking-normal text-white sm:text-2xl">
            {active.title}
          </h3>
        </div>
      </div>
      <DetailBody id={id} />
    </>
  );
}

function CapabilityDetailModal({
  open,
  id,
  onClose,
  onFormBusy,
  onFormIdle,
}: {
  open: boolean;
  id: CardId;
  onClose: () => void;
  onFormBusy: () => void;
  onFormIdle: () => void;
}) {
  const motionSafe = useMotionSafe();
  const panelRef = useRef<HTMLDivElement>(null);
  const active = CAPABILITIES.find((c) => c.id === id)!;
  const titleId = useId();
  const handleEscape = useCallback(() => onClose(), [onClose]);
  // Portal only after mount so SSR HTML matches (no document during RSC/SSR).
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  useFocusTrap(panelRef, open, handleEscape);

  useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, [open]);

  if (!mounted) return null;

  return createPortal(
    <AnimatePresence>
      {open ? (
        <motion.div
          key="why-karzar-capability-sheet"
          className="fixed inset-0 z-[80] lg:hidden"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: motionSafe ? 0.2 : 0.12 }}
        >
          <button
            type="button"
            aria-label="بستن پس‌زمینه"
            className="absolute inset-0 bg-[#0e0f0f]/55 backdrop-blur-md supports-[backdrop-filter]:bg-[#0e0f0f]/45"
            onClick={onClose}
          />

          <motion.div
            ref={panelRef}
            id={`why-karzar-modal-${id}`}
            role="dialog"
            aria-modal="true"
            aria-labelledby={titleId}
            initial={motionSafe ? { y: "100%" } : { opacity: 0 }}
            animate={motionSafe ? { y: 0 } : { opacity: 1 }}
            exit={motionSafe ? { y: "108%" } : { opacity: 0 }}
            transition={
              motionSafe
                ? { type: "spring", stiffness: 340, damping: 34, mass: 0.9 }
                : { duration: 0.15 }
            }
            className="absolute inset-x-0 bottom-0 flex max-h-[min(92dvh,40rem)] flex-col overflow-hidden rounded-t-[1.5rem] bg-[#141515] text-white shadow-[0_-24px_60px_rgba(0,0,0,0.45)]"
            onFocusCapture={(e) => {
              if (isFormControl(e.target)) onFormBusy();
            }}
            onBlurCapture={(e) => {
              const next = e.relatedTarget as Node | null;
              if (!e.currentTarget.contains(next)) onFormIdle();
            }}
            onInputCapture={() => onFormBusy()}
          >
            <div
              aria-hidden
              className="pointer-events-none absolute -end-10 -top-10 hidden h-36 w-36 rounded-full bg-[#D02327]/30 blur-3xl sm:block"
            />

            <div className="relative flex shrink-0 flex-col border-b border-white/10 px-4 pb-4 pt-[max(0.5rem,env(safe-area-inset-top))]">
              <span
                className="mx-auto mb-3 h-1 w-10 shrink-0 rounded-full bg-white/20"
                aria-hidden
              />
              <div className="flex items-start gap-3">
                <span className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-[#D02327] text-white shadow-[0_10px_24px_rgba(208,35,39,0.35)]">
                  <active.Icon set="bold" />
                </span>
                <div className="min-w-0 flex-1 pe-1">
                  <p className="text-[11px] font-bold tracking-normal text-white/45">
                    {active.index} · قابلیت کارزار
                  </p>
                  <h3
                    id={titleId}
                    className="text-lg font-black leading-[1.45] tracking-normal text-white"
                  >
                    {active.title}
                  </h3>
                </div>
                <button
                  type="button"
                  aria-label="بستن"
                  onClick={onClose}
                  className="touch-target shrink-0 rounded-xl bg-white/10 text-white transition hover:bg-white/15"
                >
                  <CloseSquare set="bold" size="small" primaryColor="currentColor" />
                </button>
              </div>
            </div>

            <div className="relative flex-1 overflow-y-auto overscroll-contain px-4 py-5 pb-[max(1.25rem,env(safe-area-inset-bottom))]">
              <DetailBody id={id} />
            </div>
          </motion.div>
        </motion.div>
      ) : null}
    </AnimatePresence>,
    document.body,
  );
}

/**
 * Capability stage — desktop side-panel; mobile opens detail + form in a sheet.
 */
function WhyKarzarHeading() {
  return (
    <>
      {/* tracking-normal: letter-spacing breaks Arabic joining on Safari/WebKit */}
      <p className="text-[11px] font-black tracking-normal text-[#D02327]">کارزار</p>
      <h2
        id="why-karzar-heading"
        className="mt-3 text-[1.55rem] font-black leading-tight tracking-normal text-white sm:text-4xl lg:text-[2.75rem]"
      >
        ابزار صنعتی، خرید مطمئن
      </h2>
    </>
  );
}

export function WhyKarzar() {
  const motionSafe = useMotionSafe();
  const [activeId, setActiveId] = useState<CardId>("proforma");
  const [formBusy, setFormBusy] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [isDesktop, setIsDesktop] = useState(false);
  const [reduceMotion, setReduceMotion] = useState(false);

  const stageRef = useRef<HTMLDivElement>(null);
  const resumeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const modalOpenRef = useRef(false);

  const clearResumeTimer = useCallback(() => {
    if (resumeTimerRef.current) {
      clearTimeout(resumeTimerRef.current);
      resumeTimerRef.current = null;
    }
  }, []);

  const pauseAutoAdvance = useCallback(() => {
    clearResumeTimer();
    setFormBusy(true);
  }, [clearResumeTimer]);

  const scheduleResume = useCallback(() => {
    clearResumeTimer();
    resumeTimerRef.current = setTimeout(() => {
      if (modalOpenRef.current) {
        setFormBusy(true);
        return;
      }
      const root = stageRef.current;
      if (root && root.contains(document.activeElement)) {
        setFormBusy(true);
        return;
      }
      setFormBusy(false);
    }, FORM_IDLE_RESUME_MS);
  }, [clearResumeTimer]);

  const closeModal = useCallback(() => {
    modalOpenRef.current = false;
    setModalOpen(false);
    scheduleResume();
  }, [scheduleResume]);

  const selectCapability = useCallback(
    (id: CardId) => {
      setActiveId(id);
      if (!window.matchMedia(LG_MQ).matches) {
        modalOpenRef.current = true;
        setModalOpen(true);
        pauseAutoAdvance();
      }
    },
    [pauseAutoAdvance],
  );

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => setReduceMotion(mq.matches);
    update();
    mq.addEventListener("change", update);
    return () => mq.removeEventListener("change", update);
  }, []);

  useEffect(() => {
    const mq = window.matchMedia(LG_MQ);
    const update = () => {
      const desktop = mq.matches;
      setIsDesktop(desktop);
      if (desktop) {
        modalOpenRef.current = false;
        setModalOpen(false);
      }
    };
    update();
    mq.addEventListener("change", update);
    return () => mq.removeEventListener("change", update);
  }, []);

  useEffect(() => () => clearResumeTimer(), [clearResumeTimer]);

  /** Auto-advance desktop panel only — skip on mobile (sheet + no stage) and reduced motion. */
  useEffect(() => {
    if (reduceMotion || formBusy || modalOpen || !isDesktop) return;

    const timer = setTimeout(() => {
      setActiveId((current) => {
        const idx = CARD_IDS.indexOf(current);
        return CARD_IDS[(idx + 1) % CARD_IDS.length]!;
      });
    }, AUTO_ADVANCE_MS);

    return () => clearTimeout(timer);
  }, [activeId, formBusy, modalOpen, reduceMotion, isDesktop]);

  return (
    <section
      aria-labelledby="why-karzar-heading"
      className="relative overflow-hidden rounded-[1.85rem] bg-[#0e0f0f] text-white"
    >
      {/* Atmosphere — static gradients only (no scroll parallax / layout motion). */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_90%_70%_at_85%_-10%,rgba(208,35,39,0.38),transparent_55%),radial-gradient(ellipse_70%_50%_at_0%_100%,rgba(94,95,94,0.22),transparent_50%)]"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-[0.045] max-md:hidden"
        style={{
          backgroundImage:
            "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E\")",
        }}
      />

      <div className="relative px-5 py-12 sm:px-8 sm:py-16 lg:px-12 lg:py-20">
        <div className="mx-auto max-w-6xl">
          {motionSafe ? (
            <motion.div
              initial={{ opacity: 0, y: 18 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.4 }}
              transition={{ duration: 0.5 }}
              className="max-w-2xl"
            >
              <WhyKarzarHeading />
            </motion.div>
          ) : (
            <div className="max-w-2xl">
              <WhyKarzarHeading />
            </div>
          )}

          <div className="mt-10 grid gap-3 lg:mt-14 lg:grid-cols-[minmax(0,0.95fr)_minmax(0,1.15fr)] lg:gap-10 lg:items-start">
            {/* Capability rail — compact on mobile (title only); no entrance stagger on max-lg */}
            <div className="flex flex-col gap-1.5 lg:gap-2" role="tablist" aria-label="قابلیت‌های کارزار">
              {CAPABILITIES.map((cap, i) => {
                // Desktop: active tab gets the white highlight (auto-advance / click).
                // Mobile: equal-weight rail — no rotating active/white state.
                const selected = isDesktop && cap.id === activeId;
                const modalActive = !isDesktop && modalOpen && cap.id === activeId;
                const tabProps = {
                  type: "button" as const,
                  role: "tab" as const,
                  id: `why-karzar-tab-${cap.id}`,
                  "aria-controls": isDesktop
                    ? `why-karzar-panel-${cap.id}`
                    : `why-karzar-modal-${cap.id}`,
                  "aria-selected": isDesktop ? selected : modalActive,
                  "aria-expanded": !isDesktop ? modalActive : undefined,
                  tabIndex: isDesktop ? (selected ? 0 : -1) : 0,
                  onClick: () => selectCapability(cap.id),
                  className: cn(
                    "group relative flex items-center gap-3 overflow-hidden rounded-2xl bg-white/[0.04] px-3.5 py-3 text-start text-white transition-colors duration-200 hover:bg-white/[0.08] sm:gap-4 sm:px-4 sm:py-3.5 lg:gap-5 lg:px-5 lg:py-5 lg:transition-all lg:duration-300",
                    // White “active” chip is desktop-only (lg+); mobile stays equal-weight.
                    selected &&
                      "lg:bg-white lg:text-[#121212] lg:shadow-[0_20px_50px_rgba(0,0,0,0.35)] lg:hover:bg-white",
                  ),
                };
                const tabInner = (
                  <>
                    <span
                      className={cn(
                        "font-black tabular-nums tracking-tight text-white/35",
                        "text-base sm:text-lg lg:text-xl",
                        selected && "lg:text-[#D02327]",
                      )}
                    >
                      {cap.index}
                    </span>
                    <span
                      className={cn(
                        "grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-white/10 text-white lg:h-11 lg:w-11 lg:transition-transform lg:duration-300 lg:group-hover:scale-105",
                        selected && "lg:bg-[#D02327] lg:text-white",
                      )}
                    >
                      <cap.Icon set="bold" />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span
                        className={cn(
                          "block text-[15px] font-black leading-[1.45] tracking-normal text-white sm:text-base lg:text-lg lg:leading-[1.5]",
                          selected && "lg:text-[#121212]",
                        )}
                      >
                        {cap.title}
                      </span>
                      <span
                        className={cn(
                          "mt-1.5 hidden text-[13px] leading-6 text-white/50 lg:block",
                          selected && "lg:text-[#5E5F5E]",
                        )}
                      >
                        {cap.teaser}
                      </span>
                    </span>
                  </>
                );

                return motionSafe ? (
                  <motion.button
                    key={cap.id}
                    {...tabProps}
                    initial={{ opacity: 0, x: 16 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true, amount: 0.35 }}
                    transition={{ duration: 0.4, delay: Math.min(0.06 * i, 0.24) }}
                  >
                    {tabInner}
                  </motion.button>
                ) : (
                  <button key={cap.id} {...tabProps}>
                    {tabInner}
                  </button>
                );
              })}
            </div>

            {/*
              Desktop detail stage: CSS grid stack keeps height = tallest panel
              so switching capabilities never jumps the layout. Hidden on mobile.
            */}
            <div
              ref={stageRef}
              className="relative hidden overflow-hidden rounded-[1.5rem] bg-gradient-to-br from-white/[0.09] to-white/[0.03] lg:grid"
              onFocusCapture={(e) => {
                if (isFormControl(e.target)) pauseAutoAdvance();
              }}
              onBlurCapture={(e) => {
                const next = e.relatedTarget as Node | null;
                if (!e.currentTarget.contains(next)) scheduleResume();
              }}
              onInputCapture={() => pauseAutoAdvance()}
            >
              <div
                aria-hidden
                className="pointer-events-none absolute -end-16 -top-16 hidden h-48 w-48 rounded-full bg-[#D02327]/25 blur-3xl lg:block"
              />

              {CAPABILITIES.map((cap) => {
                const selected = cap.id === activeId;
                return (
                  <motion.div
                    key={cap.id}
                    role="tabpanel"
                    id={`why-karzar-panel-${cap.id}`}
                    aria-labelledby={`why-karzar-tab-${cap.id}`}
                    aria-hidden={!selected}
                    inert={!selected ? true : undefined}
                    initial={false}
                    animate={{ opacity: selected ? 1 : 0 }}
                    transition={{ duration: motionSafe ? 0.28 : 0, ease: [0.25, 0.1, 0.25, 1] }}
                    className={cn(
                      "col-start-1 row-start-1 p-5 sm:p-7 lg:p-8",
                      selected ? "relative z-10" : "pointer-events-none invisible z-0",
                    )}
                  >
                    <PanelChrome id={cap.id} />
                  </motion.div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      <CapabilityDetailModal
        open={modalOpen}
        id={activeId}
        onClose={closeModal}
        onFormBusy={pauseAutoAdvance}
        onFormIdle={scheduleResume}
      />
    </section>
  );
}
