/**
 * Pure SVG mini chart components for the analytics dashboard.
 * No external charting library needed.
 */

import styles from "./analytics-page.module.css";

// ─── types ───────────────────────────────────────────────────────────────────

export type DonutSegment = {
  label: string;
  value: number;
  color: string;
};

export type BarGroup = {
  label: string;
  value: number;
  color: string;
};

// ─── DonutChart ──────────────────────────────────────────────────────────────

const DONUT_SIZE = 120;
const DONUT_RADIUS = 44;
const DONUT_STROKE = 14;
const DONUT_CENTER = DONUT_SIZE / 2;

/**
 * Renders an SVG donut (ring) chart.
 *
 * @param segments  Array of { label, value, color }
 * @param centerLabel  Text shown at the center of the ring (e.g. total count)
 * @param centerSub    Smaller subtitle below the center label
 * @param ariaLabel    Accessible label for the whole chart
 */
export function DonutChart({
  segments,
  centerLabel,
  centerSub,
  ariaLabel,
}: {
  segments: DonutSegment[];
  centerLabel?: string;
  centerSub?: string;
  ariaLabel: string;
}) {
  const total = segments.reduce((s, seg) => s + seg.value, 0);

  if (total === 0) {
    return (
      <div className={styles.donutWrap}>
        <svg
          width={DONUT_SIZE}
          height={DONUT_SIZE}
          viewBox={`0 0 ${DONUT_SIZE} ${DONUT_SIZE}`}
          role="img"
          aria-label={ariaLabel}
        >
          <circle
            cx={DONUT_CENTER}
            cy={DONUT_CENTER}
            r={DONUT_RADIUS}
            fill="none"
            stroke="color-mix(in srgb, var(--bf-border) 55%, transparent)"
            strokeWidth={DONUT_STROKE}
          />
        </svg>
      </div>
    );
  }

  const circumference = 2 * Math.PI * DONUT_RADIUS;
  let accumulated = 0;

  return (
    <div className={styles.donutWrap}>
      <svg
        width={DONUT_SIZE}
        height={DONUT_SIZE}
        viewBox={`0 0 ${DONUT_SIZE} ${DONUT_SIZE}`}
        role="img"
        aria-label={ariaLabel}
      >
        {/* background ring */}
        <circle
          cx={DONUT_CENTER}
          cy={DONUT_CENTER}
          r={DONUT_RADIUS}
          fill="none"
          stroke="color-mix(in srgb, var(--bf-border) 35%, transparent)"
          strokeWidth={DONUT_STROKE}
        />

        {/* segments — drawn as stroked circles with dasharray */}
        {segments.map((seg) => {
          if (seg.value === 0) return null;

          const pct = seg.value / total;
          const segLength = pct * circumference;
          const gapLength = circumference - segLength;
          const offset = -(accumulated * circumference) + circumference * 0.25;
          accumulated += pct;

          return (
            <circle
              key={seg.label}
              cx={DONUT_CENTER}
              cy={DONUT_CENTER}
              r={DONUT_RADIUS}
              fill="none"
              stroke={seg.color}
              strokeWidth={DONUT_STROKE}
              strokeDasharray={`${segLength} ${gapLength}`}
              strokeDashoffset={offset}
              strokeLinecap="butt"
              aria-label={`${seg.label}: ${seg.value} (${Math.round(pct * 100)}%)`}
            />
          );
        })}

        {/* center text */}
        {centerLabel && (
          <text
            x={DONUT_CENTER}
            y={centerSub ? DONUT_CENTER - 4 : DONUT_CENTER}
            textAnchor="middle"
            dominantBaseline="central"
            className={styles.donutCenterLabel}
          >
            {centerLabel}
          </text>
        )}
        {centerSub && (
          <text
            x={DONUT_CENTER}
            y={DONUT_CENTER + 12}
            textAnchor="middle"
            dominantBaseline="central"
            className={styles.donutCenterSub}
          >
            {centerSub}
          </text>
        )}
      </svg>

      {/* legend */}
      <div className={styles.donutLegend}>
        {segments.map((seg) => {
          if (seg.value === 0) return null;
          const pct = Math.round((seg.value / total) * 100);
          return (
            <div key={seg.label} className={styles.donutLegendItem}>
              <span
                className={styles.donutLegendDot}
                style={{ background: seg.color }}
              />
              <span className={styles.donutLegendLabel}>{seg.label}</span>
              <span className={styles.donutLegendValue}>
                {seg.value}
                <span className={styles.donutLegendPct}> ({pct}%)</span>
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── MiniBarChart ────────────────────────────────────────────────────────────

const BAR_CHART_WIDTH = 260;
const BAR_HEIGHT = 18;
const BAR_GAP = 10;
const LABEL_WIDTH = 72;
const VALUE_WIDTH = 36;

/**
 * Renders a horizontal bar chart.
 *
 * @param groups     Array of { label, value, color }
 * @param ariaLabel  Accessible label for the chart
 */
export function MiniBarChart({
  groups,
  ariaLabel,
}: {
  groups: BarGroup[];
  ariaLabel: string;
}) {
  const maxVal = Math.max(1, ...groups.map((g) => g.value));
  const barAreaWidth = BAR_CHART_WIDTH - LABEL_WIDTH - VALUE_WIDTH;
  const chartHeight = groups.length * (BAR_HEIGHT + BAR_GAP) - BAR_GAP + 8;

  return (
    <svg
      width="100%"
      viewBox={`0 0 ${BAR_CHART_WIDTH} ${chartHeight}`}
      role="img"
      aria-label={ariaLabel}
      className={styles.miniBarSvg}
    >
      {groups.map((g, i) => {
        const y = i * (BAR_HEIGHT + BAR_GAP) + 4;
        const barWidth = Math.max(2, (g.value / maxVal) * barAreaWidth);

        return (
          <g key={g.label} aria-label={`${g.label}: ${g.value}`}>
            {/* label */}
            <text
              x={0}
              y={y + BAR_HEIGHT / 2}
              dominantBaseline="central"
              className={styles.miniBarLabel}
            >
              {g.label}
            </text>

            {/* track */}
            <rect
              x={LABEL_WIDTH}
              y={y + 2}
              width={barAreaWidth}
              height={BAR_HEIGHT - 4}
              rx={5}
              className={styles.miniBarTrack}
            />

            {/* fill */}
            <rect
              x={LABEL_WIDTH}
              y={y + 2}
              width={barWidth}
              height={BAR_HEIGHT - 4}
              rx={5}
              fill={g.color}
            />

            {/* value */}
            <text
              x={BAR_CHART_WIDTH}
              y={y + BAR_HEIGHT / 2}
              dominantBaseline="central"
              textAnchor="end"
              className={styles.miniBarValue}
            >
              {g.value}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
