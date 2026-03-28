import { render, screen } from "@testing-library/react";
import RiskBadge from "@/components/RiskBadge";

describe("RiskBadge", () => {
  it("renders high risk label", () => {
    render(<RiskBadge riskLevel="High" riskScore={0.91} />);
    expect(screen.getByText("High (0.91)")).toBeInTheDocument();
  });

  it("renders low risk label", () => {
    render(<RiskBadge riskLevel="Low" riskScore={0.31} />);
    expect(screen.getByText("Low (0.31)")).toBeInTheDocument();
  });
});
