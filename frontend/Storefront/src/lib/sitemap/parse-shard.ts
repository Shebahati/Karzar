export function parseProductShardParam(raw: string): number | null {
  const trimmed = raw.trim();
  const withoutXml = trimmed.endsWith(".xml") ? trimmed.slice(0, -4) : trimmed;
  if (!/^\d+$/.test(withoutXml)) return null;
  const n = Number.parseInt(withoutXml, 10);
  return Number.isSafeInteger(n) && n >= 0 ? n : null;
}
