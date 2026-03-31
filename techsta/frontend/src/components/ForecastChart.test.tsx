import { render, screen } from "@testing-library/react";
import ForecastChart from "@/components/ForecastChart";
import type { ChartPayload } from "@/types/api";

const chart: ChartPayload = {
  chart_type: "line",
  labels: ["Day 1", "Day 2"],
  series: [{ name: "predicted_cases", values: [10, 20] }],
};

describe("ForecastChart", () => {
  it("shows empty message without chart", () => {
    render(
      <ForecastChart
        chart={null}
        title="Forecast"
        emptyMessage="No data yet"
      />,
    );

    expect(screen.getByText("No data yet")).toBeInTheDocument();
  });

  it("renders chart title when chart is present", () => {
    render(
      <ForecastChart
        chart={chart}
        title="Forecast"
        emptyMessage="No data yet"
      />,
    );

    expect(screen.getByText("Forecast")).toBeInTheDocument();
  });
});
