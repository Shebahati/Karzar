/** Persian copy shared by API 403, UI banner, and publish short-circuit. */
export const LEGACY_HERO_FILE_PUBLISH_DISABLED_FA =
  "انتشار مستقیم غیرفعال است؛ تغییرات از طریق استودیو جدید / دیپلوی";

export function isLegacyHeroFilePublishEnabled(): boolean {
  if (typeof window === "undefined") {
    return process.env.HERO_LEGACY_FILE_PUBLISH === "1";
  }
  return process.env.NEXT_PUBLIC_HERO_LEGACY_FILE_PUBLISH === "1";
}
