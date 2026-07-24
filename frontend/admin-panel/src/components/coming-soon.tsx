"use client";

import Link from "next/link";
import {
  ArrowRight,
  Buy,
  Category,
  Chart,
  Document,
  People,
  Setting,
  Ticket,
} from "react-iconly";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { IconlyIcon } from "@/components/layout/nav.config";

export type ComingSoonIcon =
  | "category"
  | "orders"
  | "quotes"
  | "customers"
  | "reports"
  | "documents"
  | "settings";

const ICON_MAP: Record<ComingSoonIcon, IconlyIcon> = {
  category: Category as IconlyIcon,
  orders: Buy as IconlyIcon,
  quotes: Ticket as IconlyIcon,
  customers: People as IconlyIcon,
  reports: Chart as IconlyIcon,
  documents: Document as IconlyIcon,
  settings: Setting as IconlyIcon,
};

interface ComingSoonProps {
  title: string;
  description: string;
  icon: ComingSoonIcon;
}

/**
 * Graceful placeholder for routes that exist in the navigation but are not
 * implemented yet. Keeps the sidebar fully navigable without dead 404s.
 */
export function ComingSoon({ title, description, icon }: ComingSoonProps) {
  const Icon = ICON_MAP[icon];

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-6">
      <div>
        <h2 className="text-2xl font-bold text-foreground">{title}</h2>
        <p className="mt-1 text-sm text-muted-foreground">{description}</p>
      </div>

      <Card>
        <CardContent className="flex flex-col items-center gap-5 px-6 py-20 text-center">
          <div className="flex h-20 w-20 items-center justify-center rounded-2xl bg-accent">
            <Icon set="bulk" size={42} primaryColor="#C22026" />
          </div>
          <div className="flex flex-col gap-1.5">
            <h3 className="text-lg font-bold text-foreground">این بخش در حال توسعه است</h3>
            <p className="mx-auto max-w-sm text-sm text-muted-foreground">
              ماژول «{title}» به‌زودی فعال می‌شود. در حال حاضر می‌توانید از بخش محصولات استفاده کنید.
            </p>
          </div>
          <Button asChild variant="outline" size="sm">
            <Link href="/catalog/products">
              <ArrowRight set="light" size={18} primaryColor="currentColor" />
              رفتن به مدیریت محصولات
            </Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
