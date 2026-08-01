"use client";

import Link from "next/link";
import { ChevronLeft } from "react-iconly";
import { Container } from "@/components/ui/container";
import { CatalogView } from "@/components/catalog/catalog-view";
import { resolveBrandLogoUrl } from "@/config/brand-logos";
import { formatNumber } from "@/lib/utils";
import type { Brand } from "@/types/category";

/** Brand Hub PLP shell — brand-hub-page-contract §5 / D21. */
export function BrandHubView({ brand }: { brand: Brand }) {
  const blurb = brand.meta_description?.trim() || null;
  const logo = resolveBrandLogoUrl(brand.name, brand.logo_url);

  return (
    <>
      <Container className="pt-6 pb-2">
        <nav
          aria-label="breadcrumb"
          className="mb-4 flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground"
        >
          <Link href="/" className="hover:text-primary">
            خانه
          </Link>
          <ChevronLeft size="small" set="light" />
          <Link href="/catalog" className="hover:text-primary">
            فروشگاه
          </Link>
          <ChevronLeft size="small" set="light" />
          <span className="font-bold text-foreground">{brand.name}</span>
        </nav>

        <header className="mb-6 flex max-w-3xl flex-col gap-4 sm:flex-row sm:items-start">
          {logo ? (
            // eslint-disable-next-line @next/next/no-img-element -- brand logos may be relative /uploads or remote
            <img
              src={logo}
              alt=""
              className="h-16 w-16 shrink-0 rounded-lg bg-card object-contain p-1 shadow-soft"
            />
          ) : null}
          <div className="min-w-0">
            <h1 className="text-2xl font-bold text-foreground sm:text-3xl">{brand.name}</h1>
            {typeof brand.product_count === "number" ? (
              <p className="mt-2 text-xs font-bold text-primary">
                {formatNumber(brand.product_count)} محصول این برند
              </p>
            ) : null}
            {brand.country ? (
              <p className="mt-1 text-xs text-muted-foreground">{brand.country}</p>
            ) : null}
            {blurb ? (
              <p className="mt-2 text-sm leading-7 text-muted-foreground">{blurb}</p>
            ) : null}
          </div>
        </header>
      </Container>

      <CatalogView lockedBrandId={brand.id} />
    </>
  );
}
