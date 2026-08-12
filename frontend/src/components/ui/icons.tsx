/**
 * Phoenix AI icon set — hand-drawn stroke icons replacing the emoji the UI
 * shipped with. One shared style (1.75 stroke, round caps, currentColor) so
 * every icon inherits text colour and reads as one family at any size.
 */

import type { SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement> & { size?: number };

function base({ size = 18, ...rest }: IconProps): SVGProps<SVGSVGElement> {
  return {
    width: size,
    height: size,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.75,
    strokeLinecap: "round",
    strokeLinejoin: "round",
    "aria-hidden": true,
    focusable: false,
    style: { flex: "none", verticalAlign: "-0.15em", ...rest.style },
    ...rest,
  };
}

/** Rising bar chart — business plan. */
export function IconChart(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M3 3v18h18" />
      <rect x="7" y="13" width="3" height="5" rx="0.5" />
      <rect x="12" y="9" width="3" height="9" rx="0.5" />
      <rect x="17" y="5" width="3" height="13" rx="0.5" />
    </svg>
  );
}

/** Stacked coins — credit and money. */
export function IconCoins(props: IconProps) {
  return (
    <svg {...base(props)}>
      <ellipse cx="12" cy="6" rx="7" ry="3" />
      <path d="M5 6v6c0 1.66 3.13 3 7 3s7-1.34 7-3V6" />
      <path d="M5 12v6c0 1.66 3.13 3 7 3s7-1.34 7-3v-6" />
    </svg>
  );
}

/** Receipt with a torn edge — tax. */
export function IconReceipt(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M6 2h12v20l-2-1.5L14 22l-2-1.5L10 22l-2-1.5L6 22V2z" />
      <path d="M9.5 7h5M9.5 11h5M9.5 15h3" />
    </svg>
  );
}

/** Chat bubble with a spark — the advisor. */
export function IconAdvisor(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M21 12a8 8 0 0 1-8 8H4l2.3-2.9A8 8 0 1 1 21 12z" />
      <path d="M12 8.5l.9 2.1 2.1.9-2.1.9-.9 2.1-.9-2.1-2.1-.9 2.1-.9.9-2.1z" />
    </svg>
  );
}

/** Map pin — location analysis. */
export function IconPin(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M12 21s7-5.5 7-11a7 7 0 1 0-14 0c0 5.5 7 11 7 11z" />
      <circle cx="12" cy="10" r="2.5" />
    </svg>
  );
}

/** Gift box — preferential programmes. */
export function IconGift(props: IconProps) {
  return (
    <svg {...base(props)}>
      <rect x="4" y="8" width="16" height="4" rx="0.5" />
      <path d="M6 12v8h12v-8" />
      <path d="M12 8v12" />
      <path d="M12 8s-4 0-4-2.5C8 4 10 3.5 11 4.5c.8.8 1 3.5 1 3.5zM12 8s4 0 4-2.5C16 4 14 3.5 13 4.5c-.8.8-1 3.5-1 3.5z" />
    </svg>
  );
}

/** Bank portico — bank comparison. */
export function IconBank(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M3 9l9-6 9 6H3z" />
      <path d="M5 9v8M9.5 9v8M14.5 9v8M19 9v8" />
      <path d="M3 20h18" />
    </svg>
  );
}

/** Lightbulb — recommendations. */
export function IconBulb(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M9 18h6M10 21h4" />
      <path d="M12 3a6 6 0 0 1 3.7 10.7c-.7.6-1.2 1.4-1.2 2.3H9.5c0-.9-.5-1.7-1.2-2.3A6 6 0 0 1 12 3z" />
    </svg>
  );
}

/** Sliders — assumptions used in a calculation. */
export function IconSliders(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M4 8h10M18 8h2M4 16h4M12 16h8" />
      <circle cx="16" cy="8" r="2" />
      <circle cx="10" cy="16" r="2" />
    </svg>
  );
}

/** Verdict: works. */
export function IconCheckCircle(props: IconProps) {
  return (
    <svg {...base(props)}>
      <circle cx="12" cy="12" r="9" />
      <path d="M8.5 12.5l2.3 2.3 4.7-5" />
    </svg>
  );
}

/** Verdict: borderline. */
export function IconAlertTriangle(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M12 3.5L2.5 20h19L12 3.5z" />
      <path d="M12 9.5v4.5" />
      <circle cx="12" cy="17" r="0.4" fill="currentColor" />
    </svg>
  );
}

/** Verdict: not advisable. */
export function IconXCircle(props: IconProps) {
  return (
    <svg {...base(props)}>
      <circle cx="12" cy="12" r="9" />
      <path d="M9 9l6 6M15 9l-6 6" />
    </svg>
  );
}
