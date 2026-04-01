"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import ForecastChart from "@/components/ForecastChart";
import RegionSelector from "@/components/RegionSelector";
import RiskBadge from "@/components/RiskBadge";
import SimulationSliders from "@/components/SimulationSliders";
import { runForecast, runRisk, runSimulate } from "@/lib/api";
import type {
  ChartPayload,
  ForecastResponse,
  RiskResponse,
  SimulateResponse,
} from "@/types/api";

const REGION_OPTIONS = [
  "ITA",
  "IND",
  "USA",
  "BRA",
  "GBR",
  "DEU",
  "FRA",
  "JPN",
  "ZAF",
  "AUS",
];

type SnapshotEntry = {
  id: string;
  timestamp: string;
  action: "forecast" | "simulate" | "risk";
  regionId: string;
  summary: string;
};

function forecastToChart(payload: ForecastResponse): ChartPayload {
  const points = payload.predicted_cases?.length
    ? payload.predicted_cases
    : payload.point_forecast
      ? Array.from({ length: payload.horizon_days || 7 }, () =>
          Math.round(payload.point_forecast!.predicted_roll7_cases),
        )
      : [];

  return {
    chart_type: "line",
    x_axis_label: "Day",
    y_axis_label: "Predicted Cases",
    labels: Array.from(
      { length: points.length || payload.horizon_days },
      (_, index) => `Day ${index + 1}`,
    ),
    series: [
      {
        name: "predicted_cases",
        values: points,
      },
    ],
  };
}

function simulateToChart(payload: SimulateResponse): ChartPayload {
  const points = Math.min(
    payload.baseline_cases.length,
    payload.simulated_cases.length,
  );

  return {
    chart_type: "line",
    x_axis_label: "Day",
    y_axis_label: "Cases",
    labels: Array.from({ length: points }, (_, index) => `Day ${index + 1}`),
    series: [
      {
        name: "baseline_cases",
        values: payload.baseline_cases.slice(0, points),
      },
      {
        name: "simulated_cases",
        values: payload.simulated_cases.slice(0, points),
      },
    ],
    summary: {
      delta_cases: payload.delta_cases,
    },
  };
}

export default function DashboardPage() {
  const [regionId, setRegionId] = useState("ITA");
  const [mobilityReduction, setMobilityReduction] = useState(0.3);
  const [vaccinationIncrease, setVaccinationIncrease] = useState(0.2);
  const [isLoading, setIsLoading] = useState(false);
  const [chartTitle, setChartTitle] = useState("Regional Snapshot");
  const [chartPayload, setChartPayload] = useState<ChartPayload | null>(null);
  const [riskPayload, setRiskPayload] = useState<RiskResponse | null>(null);
  const [snapshotHistory, setSnapshotHistory] = useState<SnapshotEntry[]>([]);
  const [lastSummary, setLastSummary] = useState<string>(
    "Run a forecast, simulation, or risk scan to populate this panel.",
  );
  const [lastError, setLastError] = useState<string | null>(null);

  const interventionSummary = useMemo(() => {
    const mobilityPercent = Math.round(mobilityReduction * 100);
    const vaccinationPercent = Math.round(vaccinationIncrease * 100);
    return `${mobilityPercent}% mobility reduction - ${vaccinationPercent}% vaccination increase`;
  }, [mobilityReduction, vaccinationIncrease]);

  const orderedDrivers = useMemo(() => {
    if (!riskPayload?.drivers?.length) {
      return [];
    }

    return [...riskPayload.drivers]
      .sort((a, b) => b.weight - a.weight)
      .slice(0, 5);
  }, [riskPayload]);

  const pushSnapshot = (
    action: SnapshotEntry["action"],
    region: string,
    summary: string,
  ) => {
    const entry: SnapshotEntry = {
      id: `${action}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
      timestamp: new Date().toLocaleTimeString(),
      action,
      regionId: region,
      summary,
    };

    setSnapshotHistory((previous) => [entry, ...previous].slice(0, 8));
  };

  const runForecastSnapshot = async () => {
    setIsLoading(true);
    setLastError(null);

    try {
      const forecast = await runForecast(regionId, 7);
      setChartPayload(forecastToChart(forecast));
      setChartTitle(`7-Day Forecast - ${regionId}`);
      setRiskPayload({
        region_id: forecast.region_id,
        risk_level: forecast.risk_level,
        risk_score: forecast.risk_score,
        drivers: [],
      });
      const intervalSummary = forecast.prediction_interval_80pct
        ? ` Interval q10-q90: ${forecast.prediction_interval_80pct.lower_q10.toFixed(0)}-${forecast.prediction_interval_80pct.upper_q90.toFixed(0)}.`
        : "";
      const summary = `Growth rate ${(forecast.growth_rate * 100).toFixed(1)}% with risk ${forecast.risk_level} (${forecast.risk_score.toFixed(2)}).${intervalSummary}`;
      setLastSummary(summary);
      pushSnapshot("forecast", forecast.region_id, summary);
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Unable to run forecast.";
      setLastError(message);
    } finally {
      setIsLoading(false);
    }
  };

  const runSimulationSnapshot = async () => {
    setIsLoading(true);
    setLastError(null);

    try {
      const simulation = await runSimulate(
        regionId,
        mobilityReduction,
        vaccinationIncrease,
      );
      setChartPayload(simulateToChart(simulation));
      setChartTitle(`Intervention Simulation - ${regionId}`);
      setLastSummary(simulation.impact_summary);
      pushSnapshot("simulate", simulation.region_id, simulation.impact_summary);
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Unable to run simulation.";
      setLastError(message);
    } finally {
      setIsLoading(false);
    }
  };

  const runRiskSnapshot = async () => {
    setIsLoading(true);
    setLastError(null);

    try {
      const risk = await runRisk(regionId);
      setRiskPayload(risk);
      const summary = `Risk level ${risk.risk_level} (${risk.risk_score.toFixed(2)}). ${risk.drivers.length} weighted driver(s) returned.`;
      setLastSummary(summary);
      pushSnapshot("risk", risk.region_id, summary);
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Unable to run risk scan.";
      setLastError(message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_8%_10%,#f6ffe8_0%,#cfead8_34%,#fef6e8_100%)] px-4 py-8 sm:px-6 lg:px-10">
      <section className="mx-auto grid max-w-6xl gap-4 lg:grid-cols-[minmax(0,1fr)_340px]">
        <article className="rounded-3xl border border-emerald-200 bg-white/90 p-6 shadow-[0_16px_56px_rgba(17,87,58,0.13)] backdrop-blur">
          <header className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-emerald-700">
                Regional Epidemic Intelligence
              </p>
              <h1 className="mt-2 text-3xl font-bold tracking-tight text-slate-900 font-[Space_Grotesk,ui-sans-serif,system-ui] sm:text-4xl">
                Command Overview
              </h1>
              <p className="mt-3 max-w-2xl text-sm text-slate-600">
                Use this page for fast regional snapshots. Use the dedicated
                chat route for deep multi-turn reasoning with tool traces.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Link
                href="/landing"
                className="inline-flex items-center rounded-xl border border-cyan-200 bg-cyan-50 px-4 py-2 text-sm font-semibold text-cyan-800 transition hover:bg-cyan-100"
              >
                Open Landing Experience
              </Link>
              <Link
                href="/chat"
                className="inline-flex items-center rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-2 text-sm font-semibold text-emerald-800 transition hover:bg-emerald-100"
              >
                Open Full Chat Workspace
              </Link>
            </div>
          </header>

          <div className="mt-5 grid gap-3 sm:grid-cols-3">
            <RegionSelector
              regionId={regionId}
              options={REGION_OPTIONS}
              onChange={setRegionId}
              disabled={isLoading}
            />
            <SimulationSliders
              mobilityReduction={mobilityReduction}
              vaccinationIncrease={vaccinationIncrease}
              onMobilityChange={setMobilityReduction}
              onVaccinationChange={setVaccinationIncrease}
              disabled={isLoading}
            />
          </div>

          <p className="mt-2 text-xs text-slate-600">
            Intervention profile: {interventionSummary}
          </p>

          <div className="mt-4 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={runForecastSnapshot}
              className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60"
              disabled={isLoading}
            >
              {isLoading ? "Working..." : "Run Forecast"}
            </button>
            <button
              type="button"
              onClick={runSimulationSnapshot}
              className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-800 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
              disabled={isLoading}
            >
              Run Simulation
            </button>
            <button
              type="button"
              onClick={runRiskSnapshot}
              className="rounded-xl border border-emerald-300 bg-emerald-50 px-4 py-2 text-sm font-semibold text-emerald-800 transition hover:bg-emerald-100 disabled:cursor-not-allowed disabled:opacity-60"
              disabled={isLoading}
            >
              Run Risk Scan
            </button>
          </div>

          <div className="mt-5">
            <ForecastChart
              chart={chartPayload}
              title={chartTitle}
              emptyMessage="Chart output appears here after forecast or simulation."
            />
          </div>
        </article>

        <aside className="space-y-4">
          <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <h2 className="text-sm font-semibold uppercase tracking-[0.16em] text-slate-700">
              Latest Summary
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-slate-700">
              {lastSummary}
            </p>
            {lastError ? (
              <p className="mt-3 rounded-lg border border-red-200 bg-red-50 px-2 py-1 text-xs text-red-700">
                {lastError}
              </p>
            ) : null}
          </section>

          <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <h2 className="text-sm font-semibold uppercase tracking-[0.16em] text-slate-700">
              Risk Snapshot
            </h2>
            {riskPayload ? (
              <div className="mt-3 space-y-1 text-sm text-slate-700">
                <p>
                  Region:{" "}
                  <span className="font-semibold text-slate-900">
                    {riskPayload.region_id}
                  </span>
                </p>
                <p>
                  Level:{" "}
                  <span className="font-semibold text-slate-900">
                    <RiskBadge
                      riskLevel={riskPayload.risk_level}
                      riskScore={riskPayload.risk_score}
                    />
                  </span>
                </p>
                <p>
                  Score:{" "}
                  <span className="font-semibold text-slate-900">
                    {riskPayload.risk_score.toFixed(2)}
                  </span>
                </p>

                {orderedDrivers.length ? (
                  <div className="mt-3 space-y-2 rounded-xl border border-slate-200 bg-slate-50 p-3">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-600">
                      Top Risk Drivers
                    </p>
                    {orderedDrivers.map((driver) => {
                      const weightPercent = Math.max(
                        4,
                        Math.min(100, driver.weight * 100),
                      );

                      return (
                        <div
                          key={`${driver.factor}-${driver.value}-${driver.weight}`}
                        >
                          <div className="flex items-center justify-between text-xs">
                            <span className="font-medium text-slate-700">
                              {driver.factor}
                            </span>
                            <span className="font-semibold text-slate-900">
                              {(driver.weight * 100).toFixed(0)}%
                            </span>
                          </div>
                          <progress
                            className="mt-1 h-1.5 w-full overflow-hidden rounded-full [&::-webkit-progress-bar]:bg-slate-200 [&::-webkit-progress-value]:bg-emerald-600 [&::-moz-progress-bar]:bg-emerald-600"
                            value={weightPercent}
                            max={100}
                          />
                        </div>
                      );
                    })}
                  </div>
                ) : null}
              </div>
            ) : (
              <p className="mt-3 text-sm text-slate-500">
                No risk scan has been run yet.
              </p>
            )}
          </section>

          <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <h2 className="text-sm font-semibold uppercase tracking-[0.16em] text-slate-700">
              Recent Snapshots
            </h2>
            {snapshotHistory.length ? (
              <div className="mt-3 space-y-2">
                {snapshotHistory.map((entry) => (
                  <div
                    key={entry.id}
                    className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2"
                  >
                    <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-600">
                      {entry.action} · {entry.regionId} · {entry.timestamp}
                    </p>
                    <p className="mt-1 text-xs text-slate-700">
                      {entry.summary}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="mt-3 text-sm text-slate-500">
                No runs yet. Execute forecast, simulate, or risk to build
                history.
              </p>
            )}
          </section>

          <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <h2 className="text-sm font-semibold uppercase tracking-[0.16em] text-slate-700">
              Suggested Workflow
            </h2>
            <ol className="mt-3 list-decimal space-y-1 pl-5 text-sm text-slate-700">
              <li>Pick region and intervention profile.</li>
              <li>Run forecast or simulation snapshot.</li>
              <li>Open full chat for deeper analysis and citations.</li>
            </ol>
          </section>
        </aside>
      </section>
    </main>
  );
}
