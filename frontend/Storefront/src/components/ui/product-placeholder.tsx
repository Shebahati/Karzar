/** Neutral placeholder shown instead of stock photography when a product has no image. */
export function ProductPlaceholder({
  name,
  sku,
  className,
}: {
  name?: string | null;
  sku?: string | null;
  className?: string;
}) {
  const initials = (name || sku || "ک")
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0])
    .join("");

  return (
    <div
      className={`grid h-full w-full place-items-center bg-accent text-accent-foreground ${className ?? ""}`}
    >
      <span className="text-2xl font-medium tracking-wide">{initials || "ک"}</span>
    </div>
  );
}
