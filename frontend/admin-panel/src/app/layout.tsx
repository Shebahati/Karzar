import type { Metadata, Viewport } from "next";
import { headers } from "next/headers";
import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: {
    default: "پنل مدیریت کارزار",
    template: "%s | کارزار",
  },
  description: "پنل مدیریت فروشگاه ابزارآلات صنعتی تراشکاری کارزار",
};

export const viewport: Viewport = {
  themeColor: "#C22026",
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  // Reading x-nonce opts the tree into dynamic SSR so Next can stamp matching
  // nonces on framework scripts (required with CSP strict-dynamic).
  await headers();

  return (
    <html lang="fa" dir="rtl" className="h-full">
      <body className="font-sans min-h-full bg-background text-foreground antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
