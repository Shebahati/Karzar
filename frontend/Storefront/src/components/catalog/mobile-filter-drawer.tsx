"use client";

import { useCallback, useEffect, useRef } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { CloseSquare } from "react-iconly";
import { FilterPanel } from "@/components/catalog/filter-panel";
import { Button } from "@/components/ui/button";
import { useFocusTrap } from "@/lib/use-focus-trap";
import { useMotionSafe } from "@/lib/use-motion-safe";
import { useUiStore } from "@/store/ui-store";
import { formatNumber } from "@/lib/utils";

export function MobileFilterDrawer({ productCount = 0 }: { productCount?: number }) {
  const open = useUiStore((s) => s.filterDrawerOpen);
  const setOpen = useUiStore((s) => s.setFilterDrawerOpen);
  const motionSafe = useMotionSafe();
  const panelRef = useRef<HTMLDivElement>(null);
  const handleEscape = useCallback(() => setOpen(false), [setOpen]);

  useFocusTrap(panelRef, open, handleEscape);

  useEffect(() => {
    if (!open) return;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  // In RTL, `start` is the right edge — slide in from +100% (physical right).
  const offscreen = "100%";

  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-[60] lg:hidden">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: motionSafe ? 0.2 : 0.12 }}
            onClick={() => setOpen(false)}
            className="absolute inset-0 bg-foreground/40 backdrop-blur-sm"
          />
          <motion.div
            ref={panelRef}
            initial={motionSafe ? { x: offscreen } : { opacity: 0 }}
            animate={motionSafe ? { x: 0 } : { opacity: 1 }}
            exit={motionSafe ? { x: offscreen } : { opacity: 0 }}
            transition={
              motionSafe
                ? { type: "spring", damping: 28, stiffness: 280 }
                : { duration: 0.15 }
            }
            id="mobile-filter-drawer"
            className="absolute inset-y-0 start-0 flex w-[86%] max-w-sm flex-col bg-background shadow-floating"
            role="dialog"
            aria-modal="true"
            aria-label="فیلتر محصولات"
          >
            <div className="flex items-center justify-between border-b border-border/60 px-4 pb-4 pt-[max(1rem,env(safe-area-inset-top))]">
              <h2 className="text-base font-medium text-foreground">فیلتر محصولات</h2>
              <button
                type="button"
                onClick={() => setOpen(false)}
                aria-label="بستن"
                className="touch-target rounded-lg text-muted-foreground hover:bg-muted"
              >
                <CloseSquare set="light" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-4">
              {/* Keep drawer open while adjusting filters — close via footer CTA. */}
              <FilterPanel notifyOnChange={false} />
            </div>
            <div className="border-t border-border/60 bg-card p-4 pb-[max(1rem,env(safe-area-inset-bottom))] shadow-soft">
              <Button className="w-full" onClick={() => setOpen(false)}>
                {`تأیید و بستن (${formatNumber(productCount)} محصول)`}
              </Button>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
