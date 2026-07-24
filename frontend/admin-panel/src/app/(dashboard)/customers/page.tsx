"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { People, Search } from "react-iconly";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { useCustomers } from "@/features/customers/queries";
import { ApiError } from "@/lib/api-client";
import { toPersianDigits } from "@/lib/utils";

export default function CustomersPage() {
  const [search, setSearch] = useState("");

  const listParams = useMemo(
    () => ({
      limit: 50,
      search: search.trim() || undefined,
    }),
    [search],
  );

  const { data, isPending, isError, error, refetch, isFetching } = useCustomers(listParams);
  const customers = data?.data ?? [];

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-6">
      <div>
        <h2 className="text-2xl font-bold text-[#4F4F4F]">مشتریان</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          {data ? `${data.meta.total_count.toLocaleString("fa-IR")} مشتری` : "مدیریت مشتریان"}
        </p>
      </div>

      <div className="rounded-xl bg-white p-4 shadow-sm">
        <div className="relative max-w-md">
          <span className="pointer-events-none absolute inset-y-0 start-3 flex items-center text-muted-foreground">
            <Search set="light" size={18} />
          </span>
          <Input
            placeholder="جستجو نام یا شماره موبایل..."
            className="ps-10"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      <Card className="border-transparent shadow-sm">
        <CardContent className="p-0">
          {isPending ? (
            <div className="flex flex-col gap-3 p-6">
              <Skeleton className="h-16 w-full" />
              <Skeleton className="h-16 w-full" />
            </div>
          ) : isError ? (
            <div className="flex flex-col items-center gap-3 py-16 text-center">
              <p className="text-sm font-bold">
                {error instanceof ApiError ? error.message : "خطا در دریافت مشتریان"}
              </p>
              <Button variant="outline" size="sm" onClick={() => refetch()}>
                تلاش مجدد
              </Button>
            </div>
          ) : customers.length === 0 ? (
            <div className="flex flex-col items-center gap-3 py-16 text-center">
              <People set="bulk" size={48} primaryColor="#BDBDBD" />
              <p className="text-sm font-bold text-foreground">مشتری یافت نشد</p>
            </div>
          ) : (
            <ul className={`divide-y divide-gray-100 ${isFetching ? "opacity-60" : ""}`}>
              {customers.map((customer) => (
                <li
                  key={customer.id}
                  className="flex flex-wrap items-center justify-between gap-4 px-4 py-4 hover:bg-[#F7F7F7]"
                >
                  <div>
                    <p className="text-sm font-bold text-[#4F4F4F]">
                      {customer.full_name ?? "بدون نام"}
                    </p>
                    <p className="text-xs text-muted-foreground tnum">{toPersianDigits(customer.phone)}</p>
                    <div className="mt-1.5 flex flex-wrap gap-1">
                      {customer.category && (
                        <Badge variant="outline" className="text-[10px]">
                          {customer.category}
                        </Badge>
                      )}
                      {customer.tags.slice(0, 2).map((tag) => (
                        <Badge key={tag} className="text-[10px]">
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  </div>
                  <div className="text-end text-xs text-muted-foreground">
                    <p>{customer.order_count.toLocaleString("fa-IR")} سفارش</p>
                    <p>{new Date(customer.created_at).toLocaleDateString("fa-IR")}</p>
                  </div>
                  <Button asChild variant="ghost" size="sm">
                    <Link href={`/customers/${customer.id}`}>پروفایل</Link>
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
