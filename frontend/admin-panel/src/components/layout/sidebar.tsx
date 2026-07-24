"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Logout, ChevronLeft } from "react-iconly";

import { cn } from "@/lib/utils";
import { useLogout } from "@/hooks/use-logout";
import { navSections, type NavItem } from "./nav.config";
import { LogoMark } from "./logo";

/** Widths mirrored on the layout wrapper via the `--sidebar-w` CSS variable. */
const SIDEBAR_WIDTH_EXPANDED = "18rem";
const SIDEBAR_WIDTH_COLLAPSED = "90px";

// Ensure your NavItem type in nav.config.ts supports an optional `children` array
// children?: { label: string; href: string }[];

function isActive(pathname: string, item: NavItem): boolean {
  if (item.href && item.href === "/") return pathname === "/";
  if (item.href) return item.matchPrefix ? pathname.startsWith(item.href) : pathname === item.href;
  if (item.children) return item.children.some(child => pathname.startsWith(child.href));
  return false;
}

export function Sidebar() {
  const pathname = usePathname();
  const logout = useLogout();
  
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [activeSubMenu, setActiveSubMenu] = useState<string | null>(null);
  const [hoveredTooltip, setHoveredTooltip] = useState<{
    text: string | null;
    top: number;
    right: number;
    variant: "default" | "destructive";
  }>({ text: null, top: 0, right: 0, variant: "default" });

  // Handle automatic submenu expansion based on current route
  useEffect(() => {
    navSections.forEach((section) => {
      section.items.forEach((item) => {
        if (item.children && item.children.some(child => pathname.startsWith(child.href))) {
          setActiveSubMenu(item.label);
        }
      });
    });
  }, [pathname]);

  // Publish the current sidebar width as a CSS variable so the dashboard
  // layout can indent its content without a shared React context — the
  // collapse toggle lives entirely inside this component.
  useEffect(() => {
    document.documentElement.style.setProperty(
      "--sidebar-w",
      isCollapsed ? SIDEBAR_WIDTH_COLLAPSED : SIDEBAR_WIDTH_EXPANDED,
    );
  }, [isCollapsed]);

  const handleMouseEnter = (e: React.MouseEvent, text: string, variant: "default" | "destructive" = "default") => {
    if (!isCollapsed) return;
    const rect = e.currentTarget.getBoundingClientRect();
    setHoveredTooltip({
      text,
      top: rect.top + rect.height / 2,
      // In RTL, the sidebar is on the right. We calculate the tooltip position relative to the left edge of the sidebar.
      right: window.innerWidth - rect.left + 15, 
      variant,
    });
  };

  const handleMouseLeave = () => {
    setHoveredTooltip((prev) => ({ ...prev, text: null }));
  };

  const toggleSubMenu = (label: string) => {
    if (isCollapsed) setIsCollapsed(false);
    setActiveSubMenu(prev => prev === label ? null : label);
  };

  return (
    <>
      <aside
        className={cn(
          "fixed inset-y-0 start-0 z-40 hidden flex-col bg-background shadow-lg transition-all duration-500 ease-[cubic-bezier(0.25,0.46,0.45,0.94)] lg:flex",
          isCollapsed ? "w-[90px]" : "w-72"
        )}
      >
        {/* Toggle Button */}
        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          className={cn(
            "absolute top-10 -end-4 z-50 flex h-8 w-8 cursor-pointer items-center justify-center rounded-full bg-primary text-primary-foreground shadow-md transition-all duration-300 hover:scale-110 hover:shadow-lg active:scale-95",
            "border-2 border-background"
          )}
        >
          <span
            className={cn(
              "inline-flex transition-transform duration-500",
              isCollapsed ? "rotate-180" : "rotate-0",
            )}
          >
            <ChevronLeft set="bold" size={18} />
          </span>
        </button>

        {/* Logo Section */}
        <div className="flex h-24 shrink-0 items-center justify-center overflow-hidden">
          <div className="flex items-center gap-3 transition-all duration-500">
            <div className={cn(
              "flex items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-soft transition-all duration-500",
              isCollapsed ? "h-12 w-12" : "h-11 w-11"
            )}>
              <LogoMark size={isCollapsed ? 26 : 22} />
            </div>
            <div
              className={cn(
                "flex flex-col justify-center transition-all duration-500 origin-end",
                isCollapsed ? "w-0 hidden translate-x-10 opacity-0" : "w-auto block translate-x-0 opacity-100"
              )}
            >
              <h1 className="text-xl font-bold leading-none tracking-tight text-ink">
                کارزار <span className="text-primary">.</span>
              </h1>
              <span className="text-xs font-medium text-muted-foreground mt-1">پنل مدیریت</span>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 w-full overflow-y-auto overflow-x-hidden scrollbar-hide py-4">
          <div className="flex w-full flex-col items-center space-y-2">
            {navSections.map((section, sIdx) => (
              <div key={sIdx} className="w-full flex flex-col group/menu">
                {/* Section Title */}
                <div className={cn(
                  "transition-all duration-500 overflow-hidden",
                  isCollapsed ? "h-0 opacity-0" : "h-auto opacity-100 px-6 pb-2 pt-4"
                )}>
                  <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground/50">
                    {section.title}
                  </p>
                </div>

                {/* Items */}
                {section.items.map((item) => {
                  const active = isActive(pathname, item);
                  const hasChildren = item.children && item.children.length > 0;
                  const isSubMenuActive = activeSubMenu === item.label;
                  const Icon = item.icon;

                  return (
                    <div key={item.label} className="relative w-full flex flex-col">
                      {/* Active Indicator Line */}
                      {active && (
                        <div className="absolute top-1 bottom-1 start-0 w-1 rounded-e-md bg-primary z-10 transition-all duration-500" />
                      )}

                      {hasChildren ? (
                        <button
                          onClick={() => toggleSubMenu(item.label)}
                          onMouseEnter={(e) => handleMouseEnter(e, item.label)}
                          onMouseLeave={handleMouseLeave}
                          className={cn(
                            "relative z-20 flex w-full items-center font-medium transition-all duration-300",
                            isCollapsed ? "justify-center py-4" : "gap-4 px-6 py-3",
                            active ? "text-primary" : "text-muted-foreground hover:bg-muted/50 hover:text-foreground"
                          )}
                        >
                          <div className={cn(
                            "flex h-10 w-10 shrink-0 items-center justify-center transition-all duration-300",
                            active ? "rounded-xl bg-primary text-primary-foreground shadow-md" : "text-muted-foreground/70 group-hover:text-primary"
                          )}>
                            <Icon set={active ? "bold" : "light"} size={22} />
                          </div>
                          <span className={cn(
                            "flex-1 overflow-hidden text-ellipsis whitespace-nowrap text-start text-sm font-bold transition-all duration-500 origin-end",
                            isCollapsed ? "max-w-0 opacity-0 ms-0" : "max-w-[200px] opacity-100 ms-2"
                          )}>
                            {item.label}
                          </span>
                        </button>
                      ) : (
                        <Link
                          href={item.href || "#"}
                          onMouseEnter={(e) => handleMouseEnter(e, item.label)}
                          onMouseLeave={handleMouseLeave}
                          className={cn(
                            "relative z-20 flex w-full items-center font-medium transition-all duration-300",
                            isCollapsed ? "justify-center py-4" : "gap-4 px-6 py-3",
                            active ? "text-primary" : "text-muted-foreground hover:bg-muted/50 hover:text-foreground"
                          )}
                        >
                          <div className={cn(
                            "flex h-10 w-10 shrink-0 items-center justify-center transition-all duration-300",
                            active ? "rounded-xl bg-primary text-primary-foreground shadow-md" : "text-muted-foreground/70 group-hover:text-primary"
                          )}>
                            <Icon set={active ? "bold" : "light"} size={22} />
                          </div>
                          <span className={cn(
                            "flex-1 overflow-hidden text-ellipsis whitespace-nowrap text-start text-sm font-bold transition-all duration-500 origin-end",
                            isCollapsed ? "max-w-0 opacity-0 ms-0" : "max-w-[200px] opacity-100 ms-2"
                          )}>
                            {item.label}
                          </span>
                        </Link>
                      )}

                      {/* Sub-menu implementation (if required by your config) */}
                      {hasChildren && (
                        <div className={cn(
                          "grid transition-all duration-500 ease-in-out",
                          isSubMenuActive ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0"
                        )}>
                          <div className="overflow-hidden">
                            <div className={cn(
                              "flex w-full flex-col",
                              !isCollapsed && "pe-16 ps-4 pb-4 gap-1",
                              isCollapsed && "pb-6 items-center gap-4"
                            )}>
                              {item.children?.map((child) => {
                                const childActive = pathname === child.href;
                                
                                if (isCollapsed) {
                                  return (
                                    <Link
                                      key={child.href}
                                      href={child.href}
                                      onMouseEnter={(e) => handleMouseEnter(e, child.label)}
                                      onMouseLeave={handleMouseLeave}
                                      className="relative z-30 cursor-pointer p-2 transition-transform hover:scale-125"
                                    >
                                      <div className={cn(
                                        "h-2 w-2 rounded-full transition-all duration-300",
                                        childActive ? "scale-125 bg-primary ring-2 ring-primary/20" : "bg-muted-foreground/40 hover:bg-primary/50"
                                      )} />
                                    </Link>
                                  );
                                }

                                return (
                                  <Link
                                    key={child.href}
                                    href={child.href}
                                    className="group/sub relative flex items-center gap-3 px-2 py-2 text-sm transition-colors"
                                  >
                                    <div className={cn(
                                      "h-1.5 w-1.5 shrink-0 rounded-full transition-all duration-300",
                                      childActive ? "scale-125 bg-primary shadow-sm" : "bg-muted-foreground/40 group-hover/sub:bg-muted-foreground/70"
                                    )} />
                                    <span className={cn(
                                      "overflow-hidden text-ellipsis whitespace-nowrap transition-colors",
                                      childActive ? "font-bold text-primary" : "font-medium text-muted-foreground group-hover/sub:text-foreground"
                                    )}>
                                      {child.label}
                                    </span>
                                  </Link>
                                );
                              })}
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            ))}
          </div>
        </nav>

        {/* Footer / Logout */}
        <div className="z-20 flex w-full shrink-0 items-center justify-center overflow-hidden border-t border-border/50 bg-background p-6">
          <button
            type="button"
            onClick={logout}
            onMouseEnter={(e) => handleMouseEnter(e, "خروج از حساب", "destructive")}
            onMouseLeave={handleMouseLeave}
            className={cn(
              "group relative flex items-center text-sm font-bold text-muted-foreground transition-all duration-300 hover:text-destructive",
              isCollapsed ? "h-12 w-12 justify-center rounded-xl bg-muted/30 hover:bg-destructive/10" : "w-full gap-3 rounded-lg px-4 py-3 hover:bg-destructive/5"
            )}
          >
            <Logout set="light" size={isCollapsed ? 22 : 20} />
            <span className={cn(
              "overflow-hidden whitespace-nowrap transition-all duration-300",
              isCollapsed ? "max-w-0 opacity-0" : "max-w-[100px] opacity-100"
            )}>
              خروج
            </span>
          </button>
        </div>
      </aside>

      {/* Floating Tooltip (Portal-like behavior via fixed position) */}
      {hoveredTooltip.text && (
        <div
          className="pointer-events-none fixed z-[9999] animate-in fade-in zoom-in-95 duration-200"
          style={{
            top: hoveredTooltip.top,
            right: `${hoveredTooltip.right}px`,
            transform: "translateY(-50%)",
          }}
        >
          <div className={cn(
            "whitespace-nowrap rounded-lg border px-3 py-2 text-xs font-bold shadow-md transition-colors",
            hoveredTooltip.variant === "destructive"
              ? "border-destructive/20 bg-background text-destructive"
              : "border-border/50 bg-background text-foreground"
          )}>
            {hoveredTooltip.text}
          </div>
        </div>
      )}
    </>
  );
}