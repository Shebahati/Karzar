import { STORE_NESHAN_EMBED_URL } from "@/lib/store-location";
import { cn } from "@/lib/utils";

type NeshanMapEmbedProps = {
  className?: string;
  /** iframe title for a11y */
  title?: string;
};

/**
 * Responsive Neshan place iframe — rounded frame with KarZar brand accents.
 */
export function NeshanMapEmbed({
  className,
  title = "نقشه فروشگاه کارزار روی نشان",
}: NeshanMapEmbedProps) {
  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-2xl bg-[#f4f4f4] shadow-card ring-1 ring-[#5E5F5E]/12",
        className,
      )}
    >
      {/* Soft brand corner wash — not over the map chrome */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 z-10 h-px bg-gradient-to-l from-transparent via-primary/50 to-transparent"
      />
      <div className="relative aspect-[16/10] w-full min-h-[220px] sm:min-h-[280px] lg:min-h-[320px]">
        <iframe
          title={title}
          src={STORE_NESHAN_EMBED_URL}
          className="absolute inset-0 h-full w-full border-0"
          loading="lazy"
          allowFullScreen
          referrerPolicy="no-referrer-when-downgrade"
        />
      </div>
      {/* Steel bottom lip for a framed, non-default look */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 bottom-0 z-10 h-1 bg-gradient-to-l from-[#5E5F5E]/25 via-primary/35 to-[#5E5F5E]/25"
      />
    </div>
  );
}
