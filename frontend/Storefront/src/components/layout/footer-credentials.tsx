"use client";

import { useState } from "react";
import {
  getRenderableTrustCredentials,
  TRUST_CREDENTIALS,
  TRUST_SECTION_HEADING,
  trustCredentialRel,
  type TrustCredential,
} from "@/config/trust-credentials";

const CARD_CLASS =
  "flex h-32 w-[calc(50%-0.25rem)] max-w-[7.15rem] min-w-0 flex-col items-center justify-between rounded-md border border-white/12 bg-white/[0.04] px-2 py-2 text-center no-underline outline-none transition-colors duration-150 motion-reduce:transition-none min-[380px]:w-[6.5rem] sm:w-[6.75rem] hover-fine:border-white/25 hover-fine:bg-white/[0.07] focus-visible:ring-2 focus-visible:ring-white/50";

const VISUAL_SLOT_CLASS =
  "grid h-[4.75rem] w-[4.75rem] shrink-0 place-items-center";

function CredentialDocumentIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 32 32"
      fill="none"
      className={className}
      aria-hidden
    >
      <rect
        x="8"
        y="5"
        width="16"
        height="22"
        rx="1.5"
        stroke="currentColor"
        strokeWidth="1.5"
      />
      <path
        d="M11.5 12h9M11.5 16.5h9M11.5 21h5.5"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="square"
      />
    </svg>
  );
}

function LicenseVisual({ credential }: { credential: TrustCredential }) {
  const [broken, setBroken] = useState(false);
  const src = credential.qrSrc;

  if (!src || broken) {
    return (
      <span className={VISUAL_SLOT_CLASS} aria-hidden>
        <CredentialDocumentIcon className="h-8 w-8 text-white/55" />
      </span>
    );
  }

  return (
    <span className={VISUAL_SLOT_CLASS}>
      {/* Local official QR — explicit box to avoid CLS */}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={src}
        alt=""
        width={72}
        height={72}
        loading="lazy"
        decoding="async"
        onError={() => setBroken(true)}
        className="h-[4.75rem] w-[4.75rem] object-contain"
      />
    </span>
  );
}

function EnamadMark({ credential }: { credential: TrustCredential }) {
  if (!credential.badgeSrc || !credential.enamadCode) return null;

  return (
    <span className={VISUAL_SLOT_CLASS}>
      {/* eslint-disable-next-line @next/next/no-img-element -- official enamad.ir embed */}
      <img
        referrerPolicy="origin"
        src={credential.badgeSrc}
        alt="نماد اعتماد الکترونیکی"
        style={{ cursor: "pointer" }}
        width={80}
        height={90}
        className="h-auto max-h-[76px] w-[68px] object-contain"
        {...({
          code: credential.enamadCode,
        } as React.ImgHTMLAttributes<HTMLImageElement>)}
      />
    </span>
  );
}

function CredentialCard({ credential }: { credential: TrustCredential }) {
  const href = credential.verificationUrl;
  if (!href) return null;

  return (
    <li className="min-w-0">
      <a
        href={href}
        target="_blank"
        rel={trustCredentialRel(credential)}
        referrerPolicy={credential.referrerPolicy}
        aria-label={credential.ariaLabel}
        className={CARD_CLASS}
      >
        {credential.type === "enamad" ? (
          <EnamadMark credential={credential} />
        ) : (
          <LicenseVisual credential={credential} />
        )}
        <span className="flex min-h-10 flex-col justify-end gap-0.5">
          <span
            aria-hidden
            className="line-clamp-2 text-xs font-bold leading-tight text-white/85"
          >
            {credential.title}
          </span>
          <span
            aria-hidden
            className="text-[0.6875rem] font-medium leading-tight text-white/45"
          >
            {credential.verifyLabel}
          </span>
        </span>
      </a>
    </li>
  );
}

export function FooterCredentials({
  credentials = TRUST_CREDENTIALS,
}: {
  credentials?: TrustCredential[];
}) {
  const items = getRenderableTrustCredentials(credentials);
  if (items.length === 0) return null;

  return (
    <section
      dir="rtl"
      className="min-w-0"
      aria-labelledby="footer-credentials-heading"
    >
      <h3
        id="footer-credentials-heading"
        className="text-sm font-black tracking-tight text-white"
      >
        {TRUST_SECTION_HEADING}
      </h3>
      <ul className="mt-3 flex flex-wrap gap-2 sm:gap-3">
        {items.map((credential) => (
          <CredentialCard key={credential.id} credential={credential} />
        ))}
      </ul>
    </section>
  );
}
