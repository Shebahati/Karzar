import { STORE_NESHAN_EMBED_URL } from "@/lib/store-location";
import { cn } from "@/lib/utils";

type NeshanMapEmbedProps = {
  className?: string;
  /** iframe title for a11y */
  title?: string;
};

/**
 * Soft Neshan place iframe — readable height, never hidden by contact layout.
 * Gently shorter on short monitors; still clearly a map, not a stub.
 */
export function NeshanMapEmbed({
  className,
  title = "نقشه فروشگاه کارزار روی نشان",
}: NeshanMapEmbedProps) {
  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-xl bg-muted ring-1 ring-inset ring-border/60",
        className,
      )}
    >
      <div
        className={cn(
          "relative w-full",
          "h-[11.5rem] sm:h-[13rem]",
          "[@media(max-height:720px)]:h-[9.5rem]",
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
