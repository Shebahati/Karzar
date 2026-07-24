import type { ReactNode } from "react";

import { AuthGate } from "@/components/auth-gate";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { SessionExpiryWatcher } from "@/hooks/use-session-expiry";

export default function DashboardLayout({ children }: { children: ReactNode }) {
  return (
    <AuthGate>
      <SessionExpiryWatcher />
      <div className="min-h-screen bg-background">
        <Sidebar />
        <div className="flex min-h-screen flex-col transition-[padding] duration-500 lg:ps-[var(--sidebar-w,18rem)]">
          <Header />
          <main className="flex-1 px-6 py-8 lg:px-8">{children}</main>
        </div>
      </div>
    </AuthGate>
  );
}
