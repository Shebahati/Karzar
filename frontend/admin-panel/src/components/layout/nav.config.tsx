import {
  Bag2,
  Buy,
  Call,
  Category,
  Chart,
  Document,
  Home,
  Image2,
  Message,
  People,
  Setting,
  ShieldDone,
  Ticket,
} from "react-iconly";

export interface IconlyIconProps {
  set?: "light" | "bold" | "two-tone" | "bulk" | "broken" | "curved";
  size?: number | string;
  primaryColor?: string;
  secondaryColor?: string;
  stroke?: "light" | "regular" | "bold";
}

export type IconlyIcon = (props: IconlyIconProps) => React.ReactElement;

export interface NavItem {
  label: string;
  href?: string;
  icon: IconlyIcon;
  /** Match nested routes (e.g. /catalog/products/new under /catalog). */
  matchPrefix?: boolean;
  children?: { label: string; href: string }[];
}

export interface NavSection {
  title: string;
  items: NavItem[];
}

export const navSections: NavSection[] = [
  {
    title: "عمومی",
    items: [{ label: "داشبورد", href: "/", icon: Home as IconlyIcon }],
  },
  {
    title: "فروشگاه",
    items: [
      { label: "محصولات", href: "/catalog/products", icon: Bag2 as IconlyIcon, matchPrefix: true },
      { label: "دسته‌بندی‌ها", href: "/catalog/categories", icon: Category as IconlyIcon, matchPrefix: true },
      { label: "سفارش‌ها", href: "/orders", icon: Buy as IconlyIcon, matchPrefix: true },
      { label: "استعلام‌های قیمت", href: "/quotes", icon: Ticket as IconlyIcon, matchPrefix: true },
    ],
  },
  {
    title: "محتوا (CMS)",
    items: [
      { label: "مقالات", href: "/cms/articles", icon: Document as IconlyIcon, matchPrefix: true },
      { label: "اسلایدهای هدر", href: "/cms/hero-slides", icon: Image2 as IconlyIcon, matchPrefix: true },
      { label: "نظرات محصولات", href: "/cms/comments", icon: Message as IconlyIcon, matchPrefix: true },
      { label: "پیام‌های تماس", href: "/cms/contacts", icon: Call as IconlyIcon, matchPrefix: true },
    ],
  },
  {
    title: "مدیریت",
    items: [
      { label: "مشتریان", href: "/customers", icon: People as IconlyIcon, matchPrefix: true },
      { label: "گزارش‌ها", href: "/reports", icon: Chart as IconlyIcon, matchPrefix: true },
      {
        label: "گزارش ممیزی",
        href: "/audit-logs",
        icon: ShieldDone as IconlyIcon,
        matchPrefix: true,
      },
      {
        label: "اسناد (به‌زودی)",
        href: "/documents",
        icon: Document as IconlyIcon,
        matchPrefix: true,
      },
      {
        label: "تنظیمات دستگاه",
        href: "/settings",
        icon: Setting as IconlyIcon,
        matchPrefix: true,
      },
    ],
  },
];
