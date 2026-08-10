"use client";

import { useParams } from "next/navigation";

import { StaticPageEditor } from "@/features/static-pages";

export default function StaticPageEditPage() {
  const params = useParams();
  const slug = typeof params.slug === "string" ? params.slug : "";
  return <StaticPageEditor slug={slug} />;
}
