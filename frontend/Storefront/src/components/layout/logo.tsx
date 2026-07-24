import Image from "next/image";
import Link from "next/link";
import { cn } from "@/lib/utils";

/** Karzar brand mark — square PNG logo paired with the Persian wordmark. */
export function Logo({
  className,
  showWordmark = true,
  size = 44,
}: {
  className?: string;
  showWordmark?: boolean;
  size?: number;
}) {
  return (
    <Link
      href="/"
      className={cn("flex items-center gap-2.5 font-bold", className)}
      aria-label="کارزار"
    >
      <Image
        src="/images/Karzar.png"
        alt="Karzar Logo"
        width={size}
        height={size}
        priority
        className="object-contain"
      />
      {showWordmark && (
        <span className="text-xl tracking-tight text-foreground">
          کارزار
          <span className="ms-1 text-xs font-normal text-muted-foreground">
            ابزار صنعتی
          </span>
        </span>
      )}
    </Link>
  );
}
