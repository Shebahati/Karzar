"use client";

import { useMemo, useState } from "react";
import { Call, Search } from "react-iconly";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { useContactSubmissions } from "@/features/cms/queries";
import { ApiError } from "@/lib/api-client";
import { toPersianDigits } from "@/lib/utils";

const PAGE_SIZE = 20;

export default function ContactSubmissionsPage() {
  const [search, setSearch] = useState("");
  const [phone, setPhone] = useState("");
  const [skip, setSkip] = useState(0);

  const listParams = useMemo(
    () => ({
      skip,
      limit: PAGE_SIZE,
      search: search.trim() || undefined,
      phone: phone.trim() || undefined,
    }),
    [skip, search, phone],
  );

  const { data, isPending, isError, error, refetch, isFetching } = useContactSubmissions(listParams);
  const submissions = data?.data ?? [];
  const hasFilters = Boolean(search.trim() || phone.trim());

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-6">
      <div>
        <h2 className="text-2xl font-bold text-[#4F4F4F]">پیام‌های تماس با ما</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          {data ? `${data.meta.total_count.toLocaleString("fa-IR")} پیام` : "پیام‌های ارسالی از فرم تماس با ما"}
        </p>
      </div>

      <div className="rounded-xl bg-white p-4 shadow-sm">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          <div className="relative">
            <span className="pointer-events-none absolute inset-y-0 start-3 flex items-center text-muted-foreground">
              <Search set="light" size={18} />
            </span>
            <Input
              placeholder="جستجو نام، موضوع یا کد رهگیری..."
              className="ps-10"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setSkip(0);
              }}
            />
          </div>
          <Input
            placeholder="فیلتر شماره موبایل..."
            dir="ltr"
            className="text-start tnum"
            value={phone}
            onChange={(e) => {
              setPhone(e.target.value.replace(/[^\d]/g, ""));
              setSkip(0);
            }}
          />
        </div>
        {hasFilters && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="mt-3"
            onClick={() => {
              setSearch("");
              setPhone("");
              setSkip(0);
            }}
          >
            پاک کردن فیلترها
          </Button>
        )}
      </div>

      <Card className="border-transparent shadow-sm">
        <CardContent className="p-0">
          {isPending ? (
            <div className="flex flex-col gap-3 p-6">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-20 w-full" />
              ))}
            </div>
          ) : isError ? (
            <div className="flex flex-col items-center gap-3 py-16 text-center">
              <p className="text-sm font-bold text-foreground">
                {error instanceof ApiError ? error.message : "خطا در دریافت پیام‌ها"}
              </p>
              <Button variant="outline" size="sm" onClick={() => refetch()}>
                تلاش مجدد
              </Button>
            </div>
          ) : submissions.length === 0 ? (
            <div className="flex flex-col items-center gap-3 py-16 text-center">
              <Call set="bulk" size={48} primaryColor="#BDBDBD" />
              <p className="text-sm font-bold text-foreground">پیامی یافت نشد</p>
            </div>
          ) : (
            <ul className={`divide-y divide-gray-100 ${isFetching ? "opacity-60" : ""}`}>
              {submissions.map((submission) => (
                <li key={submission.id} className="flex flex-wrap items-start justify-between gap-4 px-4 py-4">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-bold text-[#4F4F4F]">{submission.full_name}</span>
                      <Badge variant="outline" className="text-[10px] tnum" dir="ltr">
                        {submission.ticket_code}
                      </Badge>
                    </div>
                    <p className="mt-1 text-sm font-bold text-muted-foreground">{submission.subject}</p>
                    <p className="mt-1 text-sm leading-relaxed text-muted-foreground">{submission.message}</p>
                  </div>
                  <div className="text-end text-xs text-muted-foreground">
                    <p className="tnum">{toPersianDigits(submission.phone)}</p>
                    <p>{new Date(submission.created_at).toLocaleDateString("fa-IR")}</p>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      {data && data.meta.total_count > 0 && (
        <div className="flex items-center justify-between gap-3">
          <span className="text-xs text-muted-foreground">
            نمایش {toPersianDigits(skip + 1)}–{toPersianDigits(Math.min(skip + PAGE_SIZE, data.meta.total_count))} از{" "}
            {toPersianDigits(data.meta.total_count)}
          </span>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={!data.meta.has_prev}
              onClick={() => setSkip((s) => Math.max(0, s - PAGE_SIZE))}
            >
              قبلی
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={!data.meta.has_next}
              onClick={() => setSkip((s) => s + PAGE_SIZE)}
            >
              بعدی
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
