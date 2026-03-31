type RiskBadgeProps = {
  riskLevel: string;
  riskScore: number;
};

function getBadgeClasses(level: string): string {
  const normalized = level.toLowerCase();

  if (normalized === "high") {
    return "border-red-300 bg-red-50 text-red-800";
  }

  if (normalized === "medium") {
    return "border-amber-300 bg-amber-50 text-amber-800";
  }

  return "border-emerald-300 bg-emerald-50 text-emerald-800";
}

export default function RiskBadge({ riskLevel, riskScore }: RiskBadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold ${getBadgeClasses(
        riskLevel,
      )}`}
    >
      {riskLevel} ({riskScore.toFixed(2)})
    </span>
  );
}
