import { fireEvent, render, screen } from "@testing-library/react";
import RegionSelector from "@/components/RegionSelector";

describe("RegionSelector", () => {
  it("renders options and triggers onChange", () => {
    const handleChange = vi.fn();

    render(
      <RegionSelector
        regionId="ITA"
        options={["ITA", "IND"]}
        onChange={handleChange}
      />,
    );

    const select = screen.getByRole("combobox");
    fireEvent.change(select, { target: { value: "IND" } });

    expect(handleChange).toHaveBeenCalledWith("IND");
  });
});
