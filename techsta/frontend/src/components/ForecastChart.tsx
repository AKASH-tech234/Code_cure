import LineChart from "@/components/LineChart";
import type { ChartPayload } from "@/types/api";

type ForecastChartProps = {
  chart: ChartPayload | null;
  title: string;
  emptyMessage: string;
};

export default function ForecastChart({
  chart,
  title,
  emptyMessage,
}: ForecastChartProps) {
  if (!chart) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-5 text-sm text-slate-600">
        {emptyMessage}
      </div>
    );
  }

  return <LineChart chart={chart} title={title} />;
}
