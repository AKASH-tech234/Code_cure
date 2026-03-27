"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import LineChart from "@/components/LineChart";
import { runTracedEndpoint } from "@/lib/api";
import {
  clearSessionId,
  getSessionId,
  setSessionId as persistSessionId,
} from "@/lib/session";
import type {
  ApiTrace,
  ChartPayload,
  ForecastResponse,
  GatewayEndpoint,
  QueryResponse,
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

type ChatMessage = {
  id: number;
  role: "user" | "assistant";
  text: string;
  note?: string;
};

const DEBUG_TEMPLATES: Record<GatewayEndpoint, unknown> = {
  "/forecast": {
    region_id: "ITA",
    horizon_days: 7,
  },
  "/risk": {
    region_id: "ITA",
  },
  "/simulate": {
    region_id: "ITA",
    intervention: {
      mobility_reduction: 0.3,
      vaccination_increase: 0.2,
    },
  },
  "/query": {
    query: "forecast for italy",
    region_id: "ITA",
    intervention: {
      mobility_reduction: 0.3,
      vaccination_increase: 0.2,
    },
  },
};

const TRACE_HISTORY_KEY = "epi_trace_history_v1";
const MAX_TRACE_HISTORY = 20;

function isGatewayEndpoint(value: unknown): value is GatewayEndpoint {
  return (
    value === "/forecast" ||
    value === "/risk" ||
    value === "/simulate" ||
    value === "/query"
  );
}

function parseStoredTraceHistory(raw: string | null): ApiTrace[] {
  if (!raw) {
    return [];
  }

  try {
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) {
      return [];
    }

    return parsed
      .filter((entry): entry is ApiTrace => {
        if (!entry || typeof entry !== "object") {
          return false;
        }

        const candidate = entry as Record<string, unknown>;
        return (
          typeof candidate.id === "string" &&
          isGatewayEndpoint(candidate.endpoint) &&
          typeof candidate.timestamp === "string" &&
          typeof candidate.latency_ms === "number" &&
          typeof candidate.ok === "boolean"
        );
      })
      .slice(0, MAX_TRACE_HISTORY);
  } catch {
    return [];
  }
}

function toPrettyJson(value: unknown): string {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function getChartFromForecast(payload: {
  predicted_cases: number[];
  horizon_days: number;
}): ChartPayload {
  return {
    chart_type: "line",
    x_axis_label: "Day",
    y_axis_label: "Predicted Cases",
    labels: Array.from(
      { length: payload.horizon_days },
      (_, idx) => `Day ${idx + 1}`,
    ),
    series: [{ name: "predicted_cases", values: payload.predicted_cases }],
  };
}

function getChartFromSimulate(payload: {
  baseline_cases: number[];
  simulated_cases: number[];
  delta_cases: number;
}): ChartPayload {
  const labels = Array.from(
    {
      length: Math.min(
        payload.baseline_cases.length,
        payload.simulated_cases.length,
      ),
    },
    (_, idx) => `Day ${idx + 1}`,
  );

  return {
    chart_type: "line",
    x_axis_label: "Day",
    y_axis_label: "Cases",
    labels,
    series: [
      {
        name: "baseline_cases",
        values: payload.baseline_cases.slice(0, labels.length),
      },
      {
        name: "simulated_cases",
        values: payload.simulated_cases.slice(0, labels.length),
      },
    ],
    summary: {
      delta_cases: payload.delta_cases,
    },
  };
}

function getErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  return "Request failed. Please try again.";
}

function getChartTitle(response: QueryResponse): string {
  const kind = response.structured_data?.kind;
  const region = response.structured_data?.region_id || "Selected Region";

  if (kind === "simulate") {
    return `Simulation · ${region}`;
  }
  if (kind === "forecast") {
    return `Forecast · ${region}`;
  }
  if (kind === "risk") {
    return `Risk Lens · ${region}`;
  }
  return "Regional Projection";
}

export default function Home() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [regionId, setRegionId] = useState("ITA");
  const [mobilityReduction, setMobilityReduction] = useState(0.3);
  const [vaccinationIncrease, setVaccinationIncrease] = useState(0.2);
  const [queryText, setQueryText] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 1,
      role: "assistant",
      text: "Ask me about forecast, risk, or simulation and I will guide you through region-level decisions.",
    },
  ]);
  const [chartPayload, setChartPayload] = useState<ChartPayload | null>(null);
  const [chartTitle, setChartTitle] = useState("Regional Projection");
  const [isChatLoading, setIsChatLoading] = useState(false);
  const [isPanelLoading, setIsPanelLoading] = useState(false);
  const [lastError, setLastError] = useState<string | null>(null);
  const [queryMeta, setQueryMeta] = useState<{
    tool: string | null;
    intent: string | null;
    reasoning: string | null;
    sources: string[];
  } | null>(null);
  const [debugEndpoint, setDebugEndpoint] =
    useState<GatewayEndpoint>("/forecast");
  const [debugRequestText, setDebugRequestText] = useState(() =>
    toPrettyJson(DEBUG_TEMPLATES["/forecast"]),
  );
  const [traceHistory, setTraceHistory] = useState<ApiTrace[]>([]);
  const [selectedTraceId, setSelectedTraceId] = useState<string | null>(null);
  const [isDebugRunning, setIsDebugRunning] = useState(false);
  const [copiedTarget, setCopiedTarget] = useState<
    "request" | "response" | null
  >(null);

  useEffect(() => {
    const existing = getSessionId();
    if (existing) {
      setSessionId(existing);
    }

    const restoredTraces = parseStoredTraceHistory(
      window.localStorage.getItem(TRACE_HISTORY_KEY),
    );
    if (restoredTraces.length) {
      setTraceHistory(restoredTraces);
      setSelectedTraceId(restoredTraces[0].id);
    }
  }, []);

  useEffect(() => {
    window.localStorage.setItem(
      TRACE_HISTORY_KEY,
      JSON.stringify(traceHistory),
    );
  }, [traceHistory]);

  useEffect(() => {
    if (!copiedTarget) {
      return;
    }

    const timeout = window.setTimeout(() => {
      setCopiedTarget(null);
    }, 1300);

    return () => window.clearTimeout(timeout);
  }, [copiedTarget]);

  const sliderSummary = useMemo(() => {
    const mobilityPercent = Math.round(mobilityReduction * 100);
    const vaccinationPercent = Math.round(vaccinationIncrease * 100);
    return `${mobilityPercent}% mobility reduction · ${vaccinationPercent}% vaccination increase`;
  }, [mobilityReduction, vaccinationIncrease]);

  const activeTrace = useMemo(() => {
    if (!traceHistory.length) {
      return null;
    }

    if (!selectedTraceId) {
      return traceHistory[0];
    }

    return (
      traceHistory.find((entry) => entry.id === selectedTraceId) ||
      traceHistory[0]
    );
  }, [selectedTraceId, traceHistory]);

  const appendMessage = (
    role: "user" | "assistant",
    text: string,
    note?: string,
  ) => {
    setMessages((previous) => [
      ...previous,
      { id: Date.now() + Math.random(), role, text, note },
    ]);
  };

  const recordTrace = (trace: ApiTrace) => {
    setTraceHistory((previous) =>
      [trace, ...previous].slice(0, MAX_TRACE_HISTORY),
    );
    setSelectedTraceId(trace.id);
  };

  const copyActiveTraceJson = async (target: "request" | "response") => {
    if (!activeTrace) {
      return;
    }

    if (!navigator.clipboard?.writeText) {
      setLastError("Clipboard copy is not available in this browser context.");
      return;
    }

    try {
      const payload =
        target === "request"
          ? activeTrace.request_body
          : activeTrace.response_body;
      await navigator.clipboard.writeText(toPrettyJson(payload));
      setCopiedTarget(target);
    } catch {
      setLastError("Clipboard copy failed. Browser permission may be blocked.");
    }
  };

  const replayTrace = async (trace: ApiTrace) => {
    if (isDebugRunning) {
      return;
    }

    setDebugEndpoint(trace.endpoint);
    setDebugRequestText(toPrettyJson(trace.request_body));

    setIsDebugRunning(true);
    setLastError(null);

    try {
      const { trace: replayedTrace } = await runTracedEndpoint<unknown>(
        trace.endpoint,
        trace.request_body,
        "replay",
      );
      recordTrace(replayedTrace);

      if (!replayedTrace.ok) {
        setLastError(replayedTrace.error_message || "Replay request failed.");
      }
    } finally {
      setIsDebugRunning(false);
    }
  };

  const parseDebugPayload = (): unknown | null => {
    try {
      return JSON.parse(debugRequestText);
    } catch {
      setLastError("Invalid JSON payload in debug request editor.");
      return null;
    }
  };

  const setDebugTemplate = (endpoint: GatewayEndpoint) => {
    setDebugEndpoint(endpoint);
    setDebugRequestText(toPrettyJson(DEBUG_TEMPLATES[endpoint]));
  };

  const runManualDebugCall = async () => {
    const payload = parseDebugPayload();
    if (payload === null || isDebugRunning) {
      return;
    }

    setIsDebugRunning(true);
    setLastError(null);

    try {
      const { trace } = await runTracedEndpoint<unknown>(
        debugEndpoint,
        payload,
        "manual-console",
      );

      recordTrace(trace);
      if (!trace.ok) {
        setLastError(trace.error_message || "Debug request failed.");
      }
    } finally {
      setIsDebugRunning(false);
    }
  };

  const runAllGatewayTests = async () => {
    if (isDebugRunning) {
      return;
    }

    setIsDebugRunning(true);
    setLastError(null);

    const queryPayload = {
      query: "simulate for italy",
      region_id: regionId,
      intervention: {
        mobility_reduction: mobilityReduction,
        vaccination_increase: vaccinationIncrease,
      },
      session_id: sessionId || undefined,
    };

    const sequence: Array<{ endpoint: GatewayEndpoint; payload: unknown }> = [
      {
        endpoint: "/forecast",
        payload: {
          region_id: regionId,
          horizon_days: 7,
        },
      },
      {
        endpoint: "/risk",
        payload: {
          region_id: regionId,
        },
      },
      {
        endpoint: "/simulate",
        payload: {
          region_id: regionId,
          intervention: {
            mobility_reduction: mobilityReduction,
            vaccination_increase: vaccinationIncrease,
          },
        },
      },
      {
        endpoint: "/query",
        payload: queryPayload,
      },
    ];

    try {
      for (const item of sequence) {
        const { data, trace } = await runTracedEndpoint<unknown>(
          item.endpoint,
          item.payload,
          "run-all",
        );
        recordTrace(trace);

        if (!trace.ok && !lastError) {
          setLastError(`Run-all failed on ${item.endpoint}`);
        }

        if (item.endpoint === "/query") {
          const parsed = data as QueryResponse | null;
          if (parsed?.session_id) {
            setSessionId(parsed.session_id);
            persistSessionId(parsed.session_id);
          }
        }
      }
    } finally {
      setIsDebugRunning(false);
    }
  };

  const refreshForecast = async () => {
    setIsPanelLoading(true);
    setLastError(null);

    try {
      const requestBody = {
        region_id: regionId,
        horizon_days: 7,
      };
      const { data, trace } = await runTracedEndpoint<ForecastResponse>(
        "/forecast",
        requestBody,
        "controls",
      );
      recordTrace(trace);

      if (trace.ok && data) {
        setChartPayload(getChartFromForecast(data));
        setChartTitle(`Forecast · ${data.region_id}`);
      } else {
        setLastError(trace.error_message || "Forecast request failed.");
      }
    } catch (error) {
      setLastError(getErrorMessage(error));
    } finally {
      setIsPanelLoading(false);
    }
  };

  const refreshSimulation = async () => {
    setIsPanelLoading(true);
    setLastError(null);

    try {
      const requestBody = {
        region_id: regionId,
        intervention: {
          mobility_reduction: mobilityReduction,
          vaccination_increase: vaccinationIncrease,
        },
      };
      const { data, trace } = await runTracedEndpoint<SimulateResponse>(
        "/simulate",
        requestBody,
        "controls",
      );
      recordTrace(trace);

      if (trace.ok && data) {
        setChartPayload(getChartFromSimulate(data));
        setChartTitle(`Simulation · ${data.region_id}`);
      } else {
        setLastError(trace.error_message || "Simulation request failed.");
      }
    } catch (error) {
      setLastError(getErrorMessage(error));
    } finally {
      setIsPanelLoading(false);
    }
  };

  const submitQuery = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = queryText.trim();

    if (!trimmed || isChatLoading) {
      return;
    }

    appendMessage("user", trimmed);
    setQueryText("");
    setIsChatLoading(true);
    setLastError(null);

    try {
      const requestBody = {
        query: trimmed,
        session_id: sessionId || undefined,
        region_id: regionId,
        intervention: {
          mobility_reduction: mobilityReduction,
          vaccination_increase: vaccinationIncrease,
        },
      };

      const { data: response, trace } = await runTracedEndpoint<QueryResponse>(
        "/query",
        requestBody,
        "chat",
      );

      recordTrace(trace);

      if (!trace.ok || !response) {
        setLastError(trace.error_message || "Query request failed.");
        appendMessage(
          "assistant",
          `I hit an API error: ${trace.error_message || "Query request failed."}`,
        );
        return;
      }

      if (response.session_id && response.session_id !== sessionId) {
        setSessionId(response.session_id);
        persistSessionId(response.session_id);
      }

      if (response.structured_data?.chart) {
        setChartPayload(response.structured_data.chart);
        setChartTitle(getChartTitle(response));
      }

      setQueryMeta({
        tool: response.tool,
        intent: response.intent,
        reasoning: response.reasoning,
        sources: response.sources,
      });

      if (response.followup) {
        appendMessage(
          "assistant",
          response.followup.question,
          `Missing fields: ${response.followup.missing_fields.join(", ")}`,
        );
      } else {
        appendMessage("assistant", response.answer || "No answer generated.");
      }
    } catch (error) {
      const message = getErrorMessage(error);
      setLastError(message);
      appendMessage("assistant", `I hit an API error: ${message}`);
    } finally {
      setIsChatLoading(false);
    }
  };

  const resetSession = () => {
    clearSessionId();
    setSessionId(null);
    setMessages([
      {
        id: Date.now(),
        role: "assistant",
        text: "Session reset complete. Ask a fresh question whenever you are ready.",
      },
    ]);
    setQueryMeta(null);
    setLastError(null);
  };

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,#d9f5f2_0%,#f3f7e8_35%,#f5f2ec_100%)]">
      <main className="mx-auto flex w-full max-w-7xl flex-1 flex-col gap-6 px-4 py-6 sm:px-6 lg:px-10 lg:py-10">
        <header className="rounded-2xl border border-emerald-100 bg-white/80 p-5 shadow-sm backdrop-blur">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-emerald-700">
            Regional Epidemic Intelligence
          </p>
          <h1 className="mt-2 text-3xl font-bold tracking-tight text-slate-900">
            Chat-first Command Center
          </h1>
          <p className="mt-2 text-sm text-slate-600">
            Multi-turn reasoning, intervention simulation, and chart-ready
            outputs connected to your backend query contract.
          </p>
        </header>

        <section className="rounded-2xl border border-slate-300 bg-white p-5 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-lg font-semibold text-slate-900">
              API Debug Console (Gateway)
            </h2>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => activeTrace && replayTrace(activeTrace)}
                className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100 disabled:opacity-60"
                disabled={isDebugRunning || !activeTrace}
              >
                Replay Active
              </button>
              <button
                type="button"
                onClick={runManualDebugCall}
                className="rounded-lg bg-slate-900 px-3 py-2 text-sm font-semibold text-white hover:bg-slate-700 disabled:opacity-60"
                disabled={isDebugRunning}
              >
                {isDebugRunning ? "Running..." : "Run Request"}
              </button>
              <button
                type="button"
                onClick={runAllGatewayTests}
                className="rounded-lg bg-emerald-700 px-3 py-2 text-sm font-semibold text-white hover:bg-emerald-600 disabled:opacity-60"
                disabled={isDebugRunning}
              >
                Run All APIs
              </button>
            </div>
          </div>

          <div className="mt-4 grid gap-3 lg:grid-cols-[220px_1fr]">
            <label className="flex flex-col gap-2 text-sm font-medium text-slate-700">
              Endpoint
              <select
                className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
                value={debugEndpoint}
                onChange={(event) =>
                  setDebugTemplate(event.target.value as GatewayEndpoint)
                }
              >
                <option value="/forecast">POST /forecast</option>
                <option value="/risk">POST /risk</option>
                <option value="/simulate">POST /simulate</option>
                <option value="/query">POST /query</option>
              </select>
            </label>

            <label className="flex flex-col gap-2 text-sm font-medium text-slate-700">
              Request JSON (Input)
              <textarea
                className="min-h-36 rounded-lg border border-slate-300 bg-slate-950 p-3 font-mono text-xs text-emerald-200 outline-none focus:border-emerald-500"
                value={debugRequestText}
                onChange={(event) => setDebugRequestText(event.target.value)}
              />
            </label>
          </div>

          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            <div>
              <div className="flex items-center justify-between gap-2">
                <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-600">
                  Active Trace · Request JSON
                </h3>
                <button
                  type="button"
                  onClick={() => copyActiveTraceJson("request")}
                  className="rounded-md border border-slate-300 bg-white px-2 py-1 text-[11px] font-semibold text-slate-700 hover:bg-slate-100 disabled:opacity-60"
                  disabled={!activeTrace}
                >
                  {copiedTarget === "request" ? "Copied" : "Copy JSON"}
                </button>
              </div>
              <pre className="mt-2 max-h-72 overflow-auto rounded-lg border border-slate-300 bg-slate-950 p-3 text-xs text-cyan-200">
                {activeTrace
                  ? toPrettyJson(activeTrace.request_body)
                  : "No traces yet. Run a request to inspect payloads."}
              </pre>
            </div>
            <div>
              <div className="flex items-center justify-between gap-2">
                <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-600">
                  Active Trace · Response JSON
                </h3>
                <button
                  type="button"
                  onClick={() => copyActiveTraceJson("response")}
                  className="rounded-md border border-slate-300 bg-white px-2 py-1 text-[11px] font-semibold text-slate-700 hover:bg-slate-100 disabled:opacity-60"
                  disabled={!activeTrace}
                >
                  {copiedTarget === "response" ? "Copied" : "Copy JSON"}
                </button>
              </div>
              <pre className="mt-2 max-h-72 overflow-auto rounded-lg border border-slate-300 bg-slate-950 p-3 text-xs text-amber-200">
                {activeTrace
                  ? toPrettyJson(activeTrace.response_body)
                  : "No traces yet. Response body will appear here."}
              </pre>
            </div>
          </div>

          <div className="mt-4">
            <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-600">
              Trace History (latest 20)
            </h3>
            <div className="mt-2 max-h-52 space-y-2 overflow-auto rounded-lg border border-slate-200 bg-slate-50 p-2">
              {traceHistory.length === 0 && (
                <p className="px-2 py-1 text-xs text-slate-500">
                  No traces yet. Use Run Request or interact with chat and
                  controls.
                </p>
              )}
              {traceHistory.map((trace) => (
                <button
                  key={trace.id}
                  type="button"
                  onClick={() => setSelectedTraceId(trace.id)}
                  className={`w-full rounded-md border px-3 py-2 text-left text-xs ${
                    activeTrace?.id === trace.id
                      ? "border-emerald-500 bg-emerald-50"
                      : "border-slate-200 bg-white hover:bg-slate-100"
                  }`}
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-semibold text-slate-900">
                      {trace.endpoint}
                    </span>
                    <span
                      className={`rounded-full px-2 py-0.5 font-semibold ${
                        trace.ok
                          ? "bg-emerald-100 text-emerald-800"
                          : "bg-rose-100 text-rose-700"
                      }`}
                    >
                      {trace.ok
                        ? `OK ${trace.status ?? "-"}`
                        : `ERROR ${trace.status ?? "NETWORK"}`}
                    </span>
                  </div>
                  <p className="mt-1 text-slate-600">
                    {trace.source} · {trace.latency_ms}ms · {trace.timestamp}
                  </p>
                </button>
              ))}
            </div>
          </div>
        </section>

        <div className="grid gap-6 lg:grid-cols-[1.35fr_1fr]">
          <section className="flex flex-col gap-6">
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <div className="grid gap-4 md:grid-cols-2">
                <label className="flex flex-col gap-2 text-sm font-medium text-slate-700">
                  Region
                  <select
                    className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-emerald-500"
                    value={regionId}
                    onChange={(event) => setRegionId(event.target.value)}
                  >
                    {REGION_OPTIONS.map((code) => (
                      <option key={code} value={code}>
                        {code}
                      </option>
                    ))}
                  </select>
                </label>

                <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
                  <p className="font-semibold">Scenario Input</p>
                  <p className="mt-1">{sliderSummary}</p>
                </div>
              </div>

              <div className="mt-4 grid gap-4 md:grid-cols-2">
                <label className="flex flex-col gap-2 text-sm text-slate-700">
                  Mobility Reduction: {mobilityReduction.toFixed(2)}
                  <input
                    type="range"
                    min={0}
                    max={1}
                    step={0.01}
                    value={mobilityReduction}
                    onChange={(event) =>
                      setMobilityReduction(Number(event.target.value))
                    }
                  />
                </label>

                <label className="flex flex-col gap-2 text-sm text-slate-700">
                  Vaccination Increase: {vaccinationIncrease.toFixed(2)}
                  <input
                    type="range"
                    min={0}
                    max={1}
                    step={0.01}
                    value={vaccinationIncrease}
                    onChange={(event) =>
                      setVaccinationIncrease(Number(event.target.value))
                    }
                  />
                </label>
              </div>

              <div className="mt-4 flex flex-wrap gap-3">
                <button
                  type="button"
                  onClick={refreshForecast}
                  className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-700"
                  disabled={isPanelLoading}
                >
                  {isPanelLoading ? "Loading..." : "Refresh Forecast"}
                </button>
                <button
                  type="button"
                  onClick={refreshSimulation}
                  className="rounded-lg bg-emerald-700 px-4 py-2 text-sm font-semibold text-white transition hover:bg-emerald-600"
                  disabled={isPanelLoading}
                >
                  {isPanelLoading ? "Loading..." : "Simulate Scenario"}
                </button>
                <button
                  type="button"
                  onClick={resetSession}
                  className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
                >
                  Reset Session
                </button>
              </div>

              {sessionId ? (
                <p className="mt-3 text-xs text-slate-500">
                  Session: {sessionId}
                </p>
              ) : (
                <p className="mt-3 text-xs text-slate-500">
                  Session starts on first query.
                </p>
              )}
            </div>

            {chartPayload ? (
              <LineChart chart={chartPayload} title={chartTitle} />
            ) : (
              <section className="rounded-2xl border border-dashed border-slate-300 bg-white/70 p-8 text-center text-sm text-slate-500">
                Run forecast, simulation, or query with structured chart data to
                populate the visualization pane.
              </section>
            )}

            {queryMeta && (
              <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-600">
                  Latest Query Metadata
                </h3>
                <div className="mt-3 grid gap-3 text-sm text-slate-700 md:grid-cols-2">
                  <p>
                    <span className="font-semibold">Intent:</span>{" "}
                    {queryMeta.intent || "n/a"}
                  </p>
                  <p>
                    <span className="font-semibold">Tool:</span>{" "}
                    {queryMeta.tool || "n/a"}
                  </p>
                  <p className="md:col-span-2">
                    <span className="font-semibold">Reasoning:</span>{" "}
                    {queryMeta.reasoning || "n/a"}
                  </p>
                  <p className="md:col-span-2">
                    <span className="font-semibold">Sources:</span>{" "}
                    {queryMeta.sources.length
                      ? queryMeta.sources.join(", ")
                      : "none"}
                  </p>
                </div>
              </section>
            )}

            {lastError && (
              <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                {lastError}
              </div>
            )}
          </section>

          <section className="flex min-h-140 flex-col rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5">
            <h2 className="text-lg font-semibold text-slate-900">
              Conversation
            </h2>
            <div className="mt-4 flex-1 space-y-3 overflow-y-auto pr-1">
              {messages.map((message) => (
                <article
                  key={message.id}
                  className={`rounded-xl px-4 py-3 text-sm leading-relaxed ${
                    message.role === "user"
                      ? "ml-6 bg-slate-900 text-white"
                      : "mr-6 border border-slate-200 bg-slate-50 text-slate-800"
                  }`}
                >
                  <p>{message.text}</p>
                  {message.note && (
                    <p className="mt-2 text-xs font-semibold uppercase tracking-wide text-amber-700">
                      {message.note}
                    </p>
                  )}
                </article>
              ))}
            </div>

            <form className="mt-4 flex gap-2" onSubmit={submitQuery}>
              <input
                className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-emerald-500"
                placeholder="Ask: forecast for italy, simulate outbreak, risk drivers..."
                value={queryText}
                onChange={(event) => setQueryText(event.target.value)}
                disabled={isChatLoading}
              />
              <button
                type="submit"
                className="rounded-lg bg-emerald-700 px-4 py-2 text-sm font-semibold text-white transition hover:bg-emerald-600 disabled:cursor-not-allowed disabled:opacity-60"
                disabled={isChatLoading}
              >
                {isChatLoading ? "Sending..." : "Send"}
              </button>
            </form>
          </section>
        </div>
      </main>
    </div>
  );
}
