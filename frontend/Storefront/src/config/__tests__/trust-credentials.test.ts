import { describe, expect, it } from "vitest";
import {
  BUSINESS_LICENSE_ONLINE,
  BUSINESS_LICENSE_PHYSICAL,
  ENAMAD_CREDENTIAL,
  getRenderableTrustCredentials,
  isHttpsUrl,
  TRUST_CREDENTIALS,
  trustCredentialRel,
  type TrustCredential,
} from "@/config/trust-credentials";

describe("trust-credentials", () => {
  it("publishes only Enamad until business-license URLs are supplied", () => {
    expect(getRenderableTrustCredentials().map((c) => c.id)).toEqual(["enamad"]);
  });

  it("keeps the official Enamad trust URL, logo, and code unchanged", () => {
    expect(ENAMAD_CREDENTIAL.verificationUrl).toBe(
      "https://trustseal.enamad.ir/?id=6961566&Code=5F01NsyiqBFfBjNyzpNxr70bt4r065sr",
    );
    expect(ENAMAD_CREDENTIAL.badgeSrc).toBe(
      "https://trustseal.enamad.ir/logo.aspx?id=6961566&Code=5F01NsyiqBFfBjNyzpNxr70bt4r065sr",
    );
    expect(ENAMAD_CREDENTIAL.enamadCode).toBe("5F01NsyiqBFfBjNyzpNxr70bt4r065sr");
    expect(trustCredentialRel(ENAMAD_CREDENTIAL)).toBe("noopener");
    expect(trustCredentialRel(ENAMAD_CREDENTIAL)).not.toContain("noreferrer");
  });

  it("does not invent business-license identifiers, issuers, QRs, or URLs", () => {
    for (const credential of [BUSINESS_LICENSE_ONLINE, BUSINESS_LICENSE_PHYSICAL]) {
      expect(credential.verificationUrl).toBeNull();
      expect(credential.qrSrc).toBeUndefined();
      expect(credential.issuer).toBeUndefined();
      expect(credential.identifier).toBeUndefined();
    }
  });

  it("does not ship placeholder verification hosts in production config", () => {
    for (const credential of TRUST_CREDENTIALS) {
      if (!credential.verificationUrl) continue;
      expect(credential.verificationUrl).not.toMatch(
        /example\.|placeholder|localhost|127\.0\.0\.1|TODO/i,
      );
      expect(credential.verificationUrl.startsWith("https://")).toBe(true);
    }
  });

  it("accepts a business license only after a real https verification URL exists", () => {
    const online: TrustCredential = {
      ...BUSINESS_LICENSE_ONLINE,
      verificationUrl: "https://verify.test.invalid/karzar-online",
    };
    expect(getRenderableTrustCredentials([online]).map((c) => c.id)).toEqual([
      "business-license-online",
    ]);
    expect(
      getRenderableTrustCredentials([
        { ...online, verificationUrl: "http://insecure.test.invalid/x" },
      ]),
    ).toEqual([]);
    expect(
      getRenderableTrustCredentials([{ ...online, verificationUrl: null }]),
    ).toEqual([]);
  });

  it("rejects non-https values", () => {
    expect(isHttpsUrl("javascript:alert(1)")).toBe(false);
    expect(isHttpsUrl("ftp://example.com")).toBe(false);
    expect(isHttpsUrl("")).toBe(false);
    expect(isHttpsUrl(null)).toBe(false);
    expect(isHttpsUrl("https://trustseal.enamad.ir/")).toBe(true);
  });

  it("orders credentials اینماد → مجازی → حضوری", () => {
    expect(TRUST_CREDENTIALS.map((c) => c.id)).toEqual([
      "enamad",
      "business-license-online",
      "business-license-physical",
    ]);
  });
});
