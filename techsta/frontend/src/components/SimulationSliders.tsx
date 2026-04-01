type SimulationSlidersProps = {
  mobilityReduction: number;
  vaccinationIncrease: number;
  onMobilityChange: (value: number) => void;
  onVaccinationChange: (value: number) => void;
  disabled?: boolean;
};

export default function SimulationSliders({
  mobilityReduction,
  vaccinationIncrease,
  onMobilityChange,
  onVaccinationChange,
  disabled = false,
}: SimulationSlidersProps) {
  return (
    <>
      <label className="flex flex-col gap-1 text-xs font-semibold uppercase tracking-[0.14em] text-slate-600">
        Mobility
        <input
          type="range"
          min={0}
          max={1}
          step={0.05}
          value={mobilityReduction}
          onChange={(event) => onMobilityChange(Number(event.target.value))}
          disabled={disabled}
        />
      </label>

      <label className="flex flex-col gap-1 text-xs font-semibold uppercase tracking-[0.14em] text-slate-600">
        Vaccination
        <input
          type="range"
          min={0}
          max={1}
          step={0.05}
          value={vaccinationIncrease}
          onChange={(event) => onVaccinationChange(Number(event.target.value))}
          disabled={disabled}
        />
      </label>
    </>
  );
}
