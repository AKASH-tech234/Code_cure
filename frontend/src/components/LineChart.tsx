import type { ChartPayload } from "@/types/api";

type LineChartProps = {
  chart: ChartPayload;
  title: string;
};

const SERIES_COLORS = ["#1f7a8c", "#c75b12", "#3a5a40", "#8b5cf6"];
const SERIES_DOT_CLASSES = [
  "bg-cyan-700",
  "bg-orange-700",
  "bg-emerald-800",
  "bg-violet-600",
];

function roundUp(value: number): number {
  if (value <= 0) {
    return 10;
  }
  const magnitude = 10 ** Math.floor(Math.log10(value));
  return Math.ceil(value / magnitude) * magnitude;
}

export default function LineChart({ chart, title }: LineChartProps) {
  const allValues = chart.series.flatMap((series) => series.values);

  if (allValues.length === 0) {
    return (
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <h3 className="text-lg font-semibold text-slate-900">{title}</h3>
        <p className="mt-3 text-sm text-slate-500">
          No chart data available yet.
        </p>
      </section>
    );
  }

  const maxValue = Math.max(...allValues);
  const yMax = roundUp(maxValue);
  const width = 760;
  const height = 260;
  const leftPad = 52;
  const rightPad = 16;
  const topPad = 18;
  const bottomPad = 38;
  const chartWidth = width - leftPad - rightPad;
  const chartHeight = height - topPad - bottomPad;

  const toPoint = (xIndex: number, value: number, totalPoints: number) => {
    const xRatio = totalPoints <= 1 ? 0 : xIndex / (totalPoints - 1);
    const x = leftPad + xRatio * chartWidth;
    const yRatio = yMax === 0 ? 0 : value / yMax;
    const y = topPad + (1 - yRatio) * chartHeight;
    return `${x.toFixed(2)},${y.toFixed(2)}`;
  };

  const yTicks = 4;
  const tickValues = Array.from({ length: yTicks + 1 }, (_, idx) =>
    Math.round((yMax / yTicks) * (yTicks - idx)),
  );

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold text-slate-900">{title}</h3>
          <p className="text-xs text-slate-500">
            {chart.y_axis_label || "Cases"} by {chart.x_axis_label || "Day"}
          </p>
        </div>
        <div className="flex flex-wrap gap-2 text-xs text-slate-700">
          {chart.series.map((series, index) => (
            <span
              key={series.name}
              className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-3 py-1"
            >
              <span
                className={`h-2.5 w-2.5 rounded-full ${SERIES_DOT_CLASSES[index % SERIES_DOT_CLASSES.length]}`}
              />
              {series.name}
            </span>
          ))}
        </div>
      </div>

      <svg
        className="mt-4 w-full"
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label={title}
      >
        {tickValues.map((tick) => {
          const y = topPad + (1 - tick / yMax) * chartHeight;
          return (
            <g key={tick}>
              <line
                x1={leftPad}
                y1={y}
                x2={width - rightPad}
                y2={y}
                stroke="#e2e8f0"
                strokeWidth="1"
              />
              <text
                x={leftPad - 8}
                y={y + 4}
                textAnchor="end"
                fontSize="11"
                fill="#64748b"
              >
                {tick}
              </text>
            </g>
          );
        })}

        {chart.labels.map((label, idx) => {
          const xRatio =
            chart.labels.length <= 1 ? 0 : idx / (chart.labels.length - 1);
          const x = leftPad + xRatio * chartWidth;
          return (
            <text
              key={`${label}-${idx}`}
              x={x}
              y={height - 14}
              textAnchor="middle"
              fontSize="11"
              fill="#64748b"
            >
              {label}
            </text>
          );
        })}

        {chart.series.map((series, index) => {
          const points = series.values
            .map((value, pointIndex) =>
              toPoint(pointIndex, value, series.values.length),
            )
            .join(" ");
          const color = SERIES_COLORS[index % SERIES_COLORS.length];

          return (
            <polyline
              key={series.name}
              fill="none"
              stroke={color}
              strokeWidth="3"
              strokeLinecap="round"
              strokeLinejoin="round"
              points={points}
            />
          );
        })}
      </svg>
    </section>
  );
}
