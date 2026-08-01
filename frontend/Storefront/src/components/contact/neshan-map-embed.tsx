import { STORE_NESHAN_EMBED_URL } from "@/lib/store-location";
import { cn } from "@/lib/utils";

type NeshanMapEmbedProps = {
  className?: string;
  /** iframe title for a11y */
  title?: string;
};

/**
 * Compact Neshan place iframe — light frame, modest height.
 */
export function NeshanMapEmbed({
  className,
  title = "نقشه فروشگاه کارزار روی نشان",
}: NeshanMapEmbedProps) {
  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-xl bg-[#f4f4f4] ring-1 ring-inset ring-[#5E5F5E]/12",
        className,
      )}
    >
      <div className="relative aspect-[2/1] w-full min-h-[140px] max-h-[200px]">
        <iframe
          title={title}
          src={STORE_NESHAN_EMBED_URL}
          className="absolute inset-0 h-full w-full border-0"
          loading="lazy"
          allowFullScreen
          referrerPolicy="no-referrer-when-downgrade"
        />
      </div>
    </div>
  );
}
