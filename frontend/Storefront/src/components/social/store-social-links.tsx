import type { ReactNode } from "react";
import {
  STORE_INSTAGRAM_URL,
  STORE_TELEGRAM_URL,
  STORE_WHATSAPP_URL,
} from "@/lib/store-location";
import { cn } from "@/lib/utils";

const SOON_LABEL = "به‌زودی";

type SocialTone = "light" | "dark";
type SocialVariant = "pills" | "icons";

type Channel = {
  id: "telegram" | "whatsapp" | "instagram";
  label: string;
  href: string | null;
  Icon: (props: { className?: string }) => ReactNode;
};

function TelegramIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden className={className}>
      <path d="M9.78 14.65 9.6 18.3c.26 0 .37-.11.5-.24l2.4-2.3 4.98 3.66c.91.5 1.56.24 1.81-.84l3.28-15.42h.01c.27-1.27-.46-1.77-1.34-1.46L1.7 9.3C.47 9.78.49 10.48 1.48 10.78l4.94 1.54 11.47-7.22c.54-.36 1.03-.16.63.2L9.78 14.65z" />
    </svg>
  );
}

function WhatsAppIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden className={className}>
      <path d="M12.04 2C6.58 2 2.15 6.4 2.15 11.82c0 1.96.52 3.87 1.5 5.55L2 22l4.8-1.58a10 10 0 0 0 5.24 1.42h.01c5.46 0 9.89-4.4 9.89-9.82S17.5 2 12.04 2zm5.76 14.05c-.24.67-1.4 1.24-1.93 1.32-.5.07-1.13.1-1.82-.11-.42-.13-.96-.31-1.65-.61-2.9-1.25-4.78-4.17-4.93-4.36-.14-.2-1.2-1.6-1.2-3.05 0-1.45.76-2.16 1.03-2.45.27-.3.59-.37.79-.37h.57c.18 0 .43-.07.67.51.24.6.82 2.07.89 2.22.07.15.12.32.02.52-.1.2-.15.32-.3.5-.14.17-.3.38-.43.51-.14.14-.29.29-.12.57.16.28.72 1.19 1.55 1.93 1.06.95 1.96 1.25 2.24 1.39.28.14.44.12.6-.07.17-.2.7-.8.88-1.08.19-.27.37-.23.63-.14.26.1 1.64.77 1.92.91.28.14.47.21.54.33.07.12.07.69-.17 1.36z" />
    </svg>
  );
}

function InstagramIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden className={className}>
      <path d="M12 7.2A4.8 4.8 0 1 0 12 16.8 4.8 4.8 0 0 0 12 7.2zm0 7.92a3.12 3.12 0 1 1 0-6.24 3.12 3.12 0 0 1 0 6.24z" />
      <circle cx="17.34" cy="6.72" r="1.14" />
      <path d="M12 2.4c-2.6 0-2.93.01-3.95.06-1.02.05-1.72.21-2.33.45a4.7 4.7 0 0 0-1.7 1.1 4.7 4.7 0 0 0-1.1 1.7c-.24.61-.4 1.31-.45 2.33C2.41 9.07 2.4 9.4 2.4 12s.01 2.93.06 3.95c.05 1.02.21 1.72.45 2.33a4.7 4.7 0 0 0 1.1 1.7 4.7 4.7 0 0 0 1.7 1.1c.61.24 1.31.4 2.33.45 1.02.05 1.35.06 3.95.06s2.93-.01 3.95-.06c1.02-.05 1.72-.21 2.33-.45a4.7 4.7 0 0 0 1.7-1.1 4.7 4.7 0 0 0 1.1-1.7c.24-.61.4-1.31.45-2.33.05-1.02.06-1.35.06-3.95s-.01-2.93-.06-3.95c-.05-1.02-.21-1.72-.45-2.33a4.7 4.7 0 0 0-1.1-1.7 4.7 4.7 0 0 0-1.7-1.1c-.61-.24-1.31-.4-2.33-.45C14.93 2.41 14.6 2.4 12 2.4zm0 1.68c2.56 0 2.86.01 3.86.06.93.04 1.44.2 1.78.33.45.17.77.38 1.1.71.34.34.54.66.72 1.11.13.34.29.85.33 1.78.05 1 .06 1.3.06 3.86s-.01 2.86-.06 3.86c-.04.93-.2 1.44-.33 1.78-.17.45-.38.77-.71 1.1-.34.34-.66.54-1.11.72-.34.13-.85.29-1.78.33-1 .05-1.3.06-3.86.06s-2.86-.01-3.86-.06c-.93-.04-1.44-.2-1.78-.33a2.97 2.97 0 0 1-1.11-.72 2.97 2.97 0 0 1-.72-1.11c-.13-.34-.29-.85-.33-1.78-.05-1-.06-1.3-.06-3.86s.01-2.86.06-3.86c.04-.93.2-1.44.33-1.78.17-.45.38-.77.71-1.1.34-.34.66-.54 1.11-.72.34-.13.85-.29 1.78-.33 1-.05 1.3-.06 3.86-.06z" />
    </svg>
  );
}

const CHANNELS: Channel[] = [
  {
    id: "telegram",
    label: "تلگرام",
    href: STORE_TELEGRAM_URL,
    Icon: TelegramIcon,
  },
  {
    id: "whatsapp",
    label: "واتساپ",
    href: STORE_WHATSAPP_URL,
    Icon: WhatsAppIcon,
  },
  {
    id: "instagram",
    label: "اینستاگرام",
    href: STORE_INSTAGRAM_URL,
    Icon: InstagramIcon,
  },
];

type StoreSocialLinksProps = {
  tone?: SocialTone;
  variant?: SocialVariant;
  className?: string;
  /** Optional heading for contact section */
  labelledBy?: string;
};

export function StoreSocialLinks({
  tone = "light",
  variant = "pills",
  className,
  labelledBy,
}: StoreSocialLinksProps) {
  const isDark = tone === "dark";

  return (
    <nav
      aria-labelledby={labelledBy}
      aria-label={labelledBy ? undefined : "شبکه‌های اجتماعی کارزار"}
      className={cn(
        variant === "pills"
          ? "grid min-w-0 grid-cols-3 gap-2"
          : "flex min-w-0 items-center gap-2",
        className,
      )}
    >
      {CHANNELS.map(({ id, label, href, Icon }) => {
        const live = Boolean(href);
        const ariaLabel = live ? `${label} کارزار` : `${label} — ${SOON_LABEL}`;
        const title = live ? label : SOON_LABEL;

        const iconWrap = cn(
          "grid shrink-0 place-items-center transition-colors",
          variant === "pills"
            ? "h-9 w-9 rounded-xl"
            : "h-10 w-10 rounded-full",
          live
            ? isDark
              ? "bg-primary/20 text-primary group-hover:bg-primary group-hover:text-white"
              : "bg-accent text-primary group-hover:bg-primary group-hover:text-white"
            : isDark
              ? "bg-white/8 text-white/55"
              : "bg-[#5E5F5E]/10 text-[#5E5F5E]",
        );

        const shell = cn(
          "group inline-flex items-center justify-center transition",
          variant === "pills"
            ? cn(
                "min-w-0 gap-2 overflow-hidden rounded-2xl px-2.5 py-2.5 text-xs font-bold sm:px-3",
                live
                  ? isDark
                    ? "bg-white/5 text-white hover:bg-white/10"
                    : "bg-card text-foreground shadow-soft hover:shadow-card"
                  : isDark
                    ? "cursor-not-allowed bg-white/[0.03] text-white/40"
                    : "cursor-not-allowed bg-card/70 text-[#5E5F5E]/70 shadow-soft",
              )
            : cn(
                live
                  ? isDark
                    ? "rounded-full hover:scale-[1.03]"
                    : "rounded-full hover:scale-[1.03]"
                  : "cursor-not-allowed opacity-70",
              ),
        );

        const body = (
          <>
            <span className={iconWrap}>
              <Icon className="h-[1.15rem] w-[1.15rem]" />
            </span>
            {variant === "pills" ? (
              <span className="min-w-0 truncate">
                <span className="block">{label}</span>
                {!live ? (
                  <span
                    className={cn(
                      "mt-0.5 block text-[10px] font-medium",
                      isDark ? "text-white/35" : "text-[#5E5F5E]/70",
                    )}
                  >
                    {SOON_LABEL}
                  </span>
                ) : null}
              </span>
            ) : null}
            {variant === "icons" && !live ? (
              <span className="sr-only">{SOON_LABEL}</span>
            ) : null}
          </>
        );

        if (live && href) {
          return (
            <a
              key={id}
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              aria-label={ariaLabel}
              title={title}
              className={shell}
            >
              {body}
            </a>
          );
        }

        return (
          <button
            key={id}
            type="button"
            disabled
            aria-disabled="true"
            aria-label={ariaLabel}
            title={title}
            className={shell}
          >
            {body}
          </button>
        );
      })}
    </nav>
  );
}
