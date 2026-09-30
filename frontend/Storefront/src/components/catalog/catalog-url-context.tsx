"use client";

import { createContext, useContext } from "react";

const CatalogUrlContext = createContext<URLSearchParams | null>(null);

export function CatalogUrlProvider({
  value,
  children,
}: {
  value: URLSearchParams;
  children: React.ReactNode;
}) {
  return (
    <CatalogUrlContext.Provider value={value}>{children}</CatalogUrlContext.Provider>
  );
}

export function useCatalogUrlSearchParams(): URLSearchParams {
  const sp = useContext(CatalogUrlContext);
  if (!sp) {
    throw new Error("useCatalogUrlSearchParams requires CatalogUrlProvider");
  }
  return sp;
}
