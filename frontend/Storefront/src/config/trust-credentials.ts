/**
 * Official storefront trust credentials (footer «مجوزها و اعتبارها»).
 *
 * Data-integrity: never invent permit numbers, QR codes, issuers, or
 * verification URLs. A credential is published only when `verificationUrl`
 * is a real public https URL. Missing fields stay null and do not render.
 */

export const TRUST_VERIFY_LABEL = "مشاهده و استعلام";

export const TRUST_SECTION_HEADING = "مجوزها و اعتبارها";

export type TrustCredentialType = "enamad" | "business-license";

export type TrustCredentialId =
  | "enamad"
  | "business-license-online"
  | "business-license-physical";

export type TrustCredential = {
  id: TrustCredentialId;
  title: string;
  type: TrustCredentialType;
  /**
   * Official public verification destination.
   * `null` = not supplied — credential must not render.
   */
  verificationUrl: string | null;
  /** Official Enamad logo.aspx (not a locally redrawn mark). */
  badgeSrc?: string;
  /** Optional official QR asset (local public path). Never a generated fake. */
  qrSrc?: string;
  /** Issuing authority — only when known from project data. */
  issuer?: string;
  /** Permit / license identifier — only when known from project data. */
  identifier?: string;
  ariaLabel: string;
  verifyLabel: string;
  /** Enamad `code` attribute on the official <img>. */
  enamadCode?: string;
  /**
   * Enamad verification requires the document Referer. Do not add `noreferrer`.
   */
  omitNoreferrer?: boolean;
  referrerPolicy?: "origin";
};

/** Official eNamad (اینماد) — validation URL and attributes must stay unchanged. */
export const ENAMAD_CREDENTIAL: TrustCredential = {
  id: "enamad",
  title: "نماد اعتماد الکترونیکی",
  type: "enamad",
  verificationUrl:
    "https://trustseal.enamad.ir/?id=6961566&Code=5F01NsyiqBFfBjNyzpNxr70bt4r065sr",
  badgeSrc:
    "https://trustseal.enamad.ir/logo.aspx?id=6961566&Code=5F01NsyiqBFfBjNyzpNxr70bt4r065sr",
  enamadCode: "5F01NsyiqBFfBjNyzpNxr70bt4r065sr",
  ariaLabel: "استعلام نماد اعتماد الکترونیکی کارزار",
  verifyLabel: TRUST_VERIFY_LABEL,
  omitNoreferrer: true,
  referrerPolicy: "origin",
};

/**
 * پروانه کسب مجازی — unpublished until the owner supplies a real public
 * verification URL (and optionally an official QR under
 * `public/images/credentials/`).
 *
 * MISSING:
 * - verificationUrl
 * - qrSrc
 * - issuer
 * - identifier
 */
export const BUSINESS_LICENSE_ONLINE: TrustCredential = {
  id: "business-license-online",
  title: "پروانه کسب مجازی",
  type: "business-license",
  verificationUrl: null,
  qrSrc: undefined,
  issuer: undefined,
  identifier: undefined,
  ariaLabel: "استعلام پروانه کسب مجازی کارزار",
  verifyLabel: TRUST_VERIFY_LABEL,
};

/**
 * پروانه کسب حضوری — unpublished until the owner supplies a real public
 * verification URL (and optionally an official QR under
 * `public/images/credentials/`).
 *
 * MISSING:
 * - verificationUrl
 * - qrSrc
 * - issuer
 * - identifier
 */
export const BUSINESS_LICENSE_PHYSICAL: TrustCredential = {
  id: "business-license-physical",
  title: "پروانه کسب حضوری",
  type: "business-license",
  verificationUrl: null,
  qrSrc: undefined,
  issuer: undefined,
  identifier: undefined,
  ariaLabel: "استعلام پروانه کسب حضوری کارزار",
  verifyLabel: TRUST_VERIFY_LABEL,
};

/** RTL conceptual order: اینماد → مجازی → حضوری. */
export const TRUST_CREDENTIALS: TrustCredential[] = [
  ENAMAD_CREDENTIAL,
  BUSINESS_LICENSE_ONLINE,
  BUSINESS_LICENSE_PHYSICAL,
];

export function isHttpsUrl(value: string | null | undefined): value is string {
  if (!value) return false;
  try {
    const url = new URL(value);
    return url.protocol === "https:";
  } catch {
    return false;
  }
}

/** Credentials safe to show to production users. */
export function getRenderableTrustCredentials(
  credentials: readonly TrustCredential[] = TRUST_CREDENTIALS,
): TrustCredential[] {
  return credentials.filter((credential) => {
    if (!isHttpsUrl(credential.verificationUrl)) return false;
    if (credential.type === "enamad") {
      return Boolean(credential.badgeSrc && credential.enamadCode);
    }
    return true;
  });
}

export function trustCredentialRel(credential: TrustCredential): string {
  return credential.omitNoreferrer ? "noopener" : "noopener noreferrer";
}
