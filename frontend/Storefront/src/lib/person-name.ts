/** Split a stored `full_name` into given / family for form fields. */
export function splitFullName(full: string): { first: string; last: string } {
  const parts = full.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return { first: "", last: "" };
  if (parts.length === 1) return { first: parts[0], last: "" };
  return { first: parts[0], last: parts.slice(1).join(" ") };
}

/** Join first + last into a single `full_name` for the profile API. */
export function joinFullName(first: string, last: string): string {
  return `${first.trim()} ${last.trim()}`.trim();
}
