import type { ReactNode } from "react";

export type NicheIconKey = "graduation-cap" | "stethoscope" | "code" | "briefcase" | (string & {});

type Props = {
  iconKey: string;
  className?: string;
};

function GradientDefs() {
  return (
    <defs>
      <linearGradient id="nicheGrad" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#a78bfa" />
        <stop offset="100%" stopColor="#60a5fa" />
      </linearGradient>
      <linearGradient id="nicheGradSoft" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#a78bfa" stopOpacity="0.45" />
        <stop offset="100%" stopColor="#60a5fa" stopOpacity="0.45" />
      </linearGradient>
    </defs>
  );
}

export function NicheIconByKey({ iconKey, className }: Props): ReactNode {
  const cls = className ?? "";
  if (iconKey === "graduation-cap") {
    return (
      <svg className={cls} viewBox="0 0 24 24" fill="none" aria-hidden>
        <GradientDefs />
        <path
          d="M3 10.5 12 6l9 4.5-9 4.5L3 10.5Z"
          stroke="url(#nicheGrad)"
          strokeWidth="1.5"
          fill="url(#nicheGradSoft)"
          fillOpacity="0.15"
        />
        <path
          d="M7 12.5V16c0 1.2 2.1 2.2 5 2.2s5-1 5-2.2v-3.5"
          stroke="url(#nicheGrad)"
          strokeWidth="1.5"
          strokeLinecap="round"
        />
        <line x1="21" y1="10.5" x2="21" y2="17" stroke="url(#nicheGrad)" strokeWidth="1.5" strokeLinecap="round" />
        <circle cx="21" cy="17.5" r="1" fill="url(#nicheGrad)" />
      </svg>
    );
  }
  if (iconKey === "stethoscope") {
    return (
      <svg className={cls} viewBox="0 0 24 24" fill="none" aria-hidden>
        <GradientDefs />
        <path d="M8 4v4a4 4 0 0 0 8 0V4" stroke="url(#nicheGrad)" strokeWidth="1.5" strokeLinecap="round" />
        <path d="M6 4h4" stroke="url(#nicheGrad)" strokeWidth="1.5" strokeLinecap="round" />
        <path d="M14 4h4" stroke="url(#nicheGrad)" strokeWidth="1.5" strokeLinecap="round" />
        <path
          d="M16 12v2a4 4 0 0 1-8 0v-1"
          stroke="url(#nicheGradSoft)"
          strokeWidth="1.25"
          strokeLinecap="round"
          strokeDasharray="2 2"
        />
        <circle cx="19" cy="16" r="2.5" stroke="url(#nicheGrad)" strokeWidth="1.5" />
        <circle cx="19" cy="16" r="0.8" fill="url(#nicheGrad)" />
        <path d="M16 13v1a1 1 0 0 0 1 1h0" stroke="url(#nicheGrad)" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
    );
  }
  if (iconKey === "code") {
    return (
      <svg className={cls} viewBox="0 0 24 24" fill="none" aria-hidden>
        <GradientDefs />
        <rect x="2" y="3" width="20" height="18" rx="3" stroke="url(#nicheGradSoft)" strokeWidth="1.25" />
        <path d="M9 9L5 12l4 3" stroke="url(#nicheGrad)" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M15 9l4 3-4 3" stroke="url(#nicheGrad)" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M13 6l-2 12" stroke="url(#nicheGrad)" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
    );
  }
  // briefcase / services / default
  return (
    <svg className={cls} viewBox="0 0 24 24" fill="none" aria-hidden>
      <GradientDefs />
      <rect x="2" y="9" width="20" height="11" rx="2.5" stroke="url(#nicheGrad)" strokeWidth="1.5" />
      <path
        d="M8 9V7a4 4 0 0 1 8 0v2"
        stroke="url(#nicheGrad)"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
      <path
        d="M2 14h20"
        stroke="url(#nicheGradSoft)"
        strokeWidth="1"
      />
      <rect x="10" y="12.5" width="4" height="3" rx="0.75" fill="url(#nicheGrad)" fillOpacity="0.25" stroke="url(#nicheGrad)" strokeWidth="1" />
    </svg>
  );
}
