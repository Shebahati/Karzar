"use client";

import { useEffect, useState } from "react";
import { InfoCircle, Lock, Setting } from "react-iconly";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { env } from "@/config/env";
import {
  DEFAULT_ADMIN_SETTINGS,
  getAdminSettings,
  saveAdminSettings,
  type AdminStoreSettings,
} from "@/lib/admin-settings";

export default function SettingsPage() {
  const [settings, setSettings] = useState<AdminStoreSettings>(DEFAULT_ADMIN_SETTINGS);

  useEffect(() => {
    setSettings(getAdminSettings());
    const sync = () => setSettings(getAdminSettings());
    window.addEventListener("karzar-admin-settings-change", sync);
    return () => window.removeEventListener("karzar-admin-settings-change", sync);
  }, []);

  function update<K extends keyof AdminStoreSettings>(key: K, value: AdminStoreSettings[K]) {
    setSettings((prev) => ({ ...prev, [key]: value }));
  }

  const handleSave = () => {
    saveAdminSettings(settings);
    toast.success("تنظیمات ذخیره شد");
  };

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6">
      <div className="rounded-lg border border-warning/40 bg-warning/10 px-4 py-3 text-sm leading-6 text-foreground">
        این تنظیمات فقط روی <strong>همین مرورگر</strong> ذخیره می‌شود و فروشگاه عمومی / API را
        کنترل نمی‌کند. خاموش‌کردن استعلام در اینجا مسیر <code>/quote</code> را حذف نمی‌کند.
      </div>

      <div>
        <h2 className="text-2xl font-bold text-foreground">تنظیمات دستگاه</h2>
        <p className="mt-1 text-sm text-muted-foreground">ترجیحات محلی پنل (localStorage)</p>
      </div>

      <div className="flex items-start gap-3 rounded-xl bg-warning/10 p-4">
        <span className="mt-0.5 shrink-0 text-warning">
          <InfoCircle set="bulk" size={20} primaryColor="#B45309" />
        </span>
        <div className="text-sm leading-6">
          <p className="font-bold text-foreground">این تنظیمات فقط روی همین مرورگر ذخیره می‌شود</p>
          <p className="mt-1 text-muted-foreground">
            مقادیر این صفحه در حافظه محلی (localStorage) این دستگاه نگه‌داری می‌شوند و روی فروشگاه
            (استوری‌فرانت) یا سایر مدیران اعمال نمی‌گردند. برای تغییر واقعی تنظیمات فروشگاه، نیاز به
            اتصال این بخش به backend است.
          </p>
        </div>
      </div>

      <Card>
        <CardContent className="flex flex-col gap-6 p-6">
          <div className="flex items-center gap-2 text-sm font-bold text-foreground">
            <Setting set="bulk" size={20} primaryColor="#C22026" />
            اطلاعات فروشگاه
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="shop-name">نام فروشگاه</Label>
            <Input
              id="shop-name"
              value={settings.shop_name}
              onChange={(e) => update("shop_name", e.target.value)}
            />
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="support-phone">تلفن پشتیبانی</Label>
            <Input
              id="support-phone"
              value={settings.support_phone}
              onChange={(e) => update("support_phone", e.target.value)}
              className="tnum"
            />
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="order-note">یادداشت سفارش</Label>
            <Textarea
              id="order-note"
              value={settings.min_order_note}
              onChange={(e) => update("min_order_note", e.target.value)}
              rows={3}
            />
          </div>

          <div className="flex items-center justify-between rounded-lg bg-muted/50 px-4 py-3">
            <div>
              <p className="text-sm font-bold text-foreground">یادداشت محلی: استعلام قیمت</p>
              <p className="text-xs leading-5 text-muted-foreground">
                این کلید فقط یادآوری برای این دستگاه است و مسیر استعلام واقعی فروشگاه را روشن/خاموش
                نمی‌کند.
              </p>
            </div>
            <Switch
              checked={settings.inquiry_enabled}
              onCheckedChange={(v) => update("inquiry_enabled", v)}
            />
          </div>

          <div className="rounded-xl border border-primary/20 bg-accent/30 p-4">
            <div className="flex items-start justify-between gap-4">
              <div className="flex gap-3">
                <span className="grid h-10 w-10 place-items-center rounded-xl bg-primary/10">
                  <Lock set="bulk" size={20} primaryColor="#C22026" />
                </span>
                <div>
                  <p className="text-sm font-bold text-foreground">ورود نیازمند رمز عبور</p>
                  <p className="mt-1 text-xs leading-5 text-muted-foreground">
                    فقط در حالت mock می‌توانید رمز را اختیاری کنید. در live همیشه اجباری است.
                  </p>
                </div>
              </div>
              <Switch
                checked={env.USE_MOCK ? settings.require_password_for_login : true}
                disabled={!env.USE_MOCK}
                onCheckedChange={(v) => update("require_password_for_login", v)}
              />
            </div>
          </div>

          <Button type="button" onClick={handleSave} className="self-start">
            ذخیره تنظیمات
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
