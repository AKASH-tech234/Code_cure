type RegionSelectorProps = {
  regionId: string;
  options: string[];
  onChange: (regionId: string) => void;
  disabled?: boolean;
};

export default function RegionSelector({
  regionId,
  options,
  onChange,
  disabled = false,
}: RegionSelectorProps) {
  return (
    <label className="flex flex-col gap-1 text-xs font-semibold uppercase tracking-[0.14em] text-slate-600">
      Region
      <select
        value={regionId}
        onChange={(event) => onChange(event.target.value)}
        className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-900 focus:border-emerald-500 focus:outline-none"
        disabled={disabled}
      >
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </label>
  );
}
