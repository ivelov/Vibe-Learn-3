"use client";

interface SparklineProps {
  data: number[];
  width?: number;
  height?: number;
  color?: string;
}

/**
 * Minimal dependency-free SVG sparkline. Renders a polyline scaled to the
 * min/max of the provided series. Returns a flat baseline when there are
 * fewer than two points.
 */
export function Sparkline({
  data,
  width = 80,
  height = 24,
  color = "#209dd7",
}: SparklineProps) {
  if (!data || data.length < 2) {
    return (
      <svg width={width} height={height} className="opacity-40">
        <line
          x1={0}
          y1={height / 2}
          x2={width}
          y2={height / 2}
          stroke={color}
          strokeWidth={1}
          strokeDasharray="2 2"
        />
      </svg>
    );
  }

  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const stepX = width / (data.length - 1);
  const pad = 2;
  const usableH = height - pad * 2;

  const points = data
    .map((v, i) => {
      const x = i * stepX;
      const y = pad + usableH - ((v - min) / range) * usableH;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="none"
    >
      <polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth={1.5}
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  );
}
