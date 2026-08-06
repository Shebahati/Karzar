import { STORE_NESHAN_EMBED_URL } from "@/lib/store-location";
import { cn } from "@/lib/utils";

type NeshanMapEmbedProps = {
  className?: string;
  /** iframe title for a11y */
  title?: string;
};

/**
 * Compact Neshan place iframe — height scales with viewport so short
 * monitors keep the map in the first scroll without a tall aspect box.
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
      <div
        className={cn(
          "relative w-full",
          /* Prefer svh (stable) with dvh fallthrough via min(); clamp keeps a readable map */
          "h-[clamp(5.25rem,min(16svh,18dvh),10.5rem)]",
          "[@media(max-height:760px)]:h-[clamp(4.5rem,12svh,7.5rem)]",
          "[@media(max-height:640px)]:h-[clamp(4rem,10svh,6.25rem)]",
        )}
      >
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
