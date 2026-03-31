"use client";

import { FormEvent, useMemo, useState } from "react";
import Link from "next/link";
import ChatPanel from "@/components/ChatPanel";
import ExplanationPanel from "@/components/ExplanationPanel";
import ForecastChart from "@/components/ForecastChart";
import RegionSelector from "@/components/RegionSelector";
import SimulationSliders from "@/components/SimulationSliders";
import { runTracedEndpoint } from "@/lib/api";
import { clearSessionId, getSessionId, setSessionId } from "@/lib/session";
import type { QueryRequest, QueryResponse } from "@/types/api";

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
  hint?: string;
};

const QUICK_PROMPTS = [
  "Forecast India for the next 7 days",
  "Assess outbreak risk in Italy",
  "Simulate USA with 30% mobility reduction and 20% vaccination increase",
  "Summarize the Mendeley AMR dataset",
];

function normalizeAnswer(response: QueryResponse): string {
  if (response.answer && response.answer.trim()) {
    return response.answer;
  }
  if (response.followup?.question) {
    return response.followup.question;
  }
  return "I could not generate an answer yet. Please add more context and retry.";
}

export default function ChatPage() {
  const [query, setQuery] = useState("");
  const [regionId, setRegionId] = useState("ITA");
  const [mobilityReduction, setMobilityReduction] = useState(0.3);
  const [vaccinationIncrease, setVaccinationIncrease] = useState(0.2);
  const [isLoading, setIsLoading] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 1,
      role: "assistant",
      text: "I am ready for forecasting, risk, simulation, and context-grounded RAG questions.",
      hint: "Try: Simulate India with 40% mobility reduction and 20% vaccination increase",
    },
  ]);
  const [lastResponse, setLastResponse] = useState<QueryResponse | null>(null);
  const [lastTraceMeta, setLastTraceMeta] = useState<{
    latencyMs: number;
    status: number | null;
    ok: boolean;
  } | null>(null);
  const [lastError, setLastError] = useState<string | null>(null);

  const sliderSummary = useMemo(() => {
    const mobilityPercent = Math.round(mobilityReduction * 100);
    const vaccinationPercent = Math.round(vaccinationIncrease * 100);
    return `${mobilityPercent}% mobility reduction, ${vaccinationPercent}% vaccination increase`;
  }, [mobilityReduction, vaccinationIncrease]);

  const chartPayload = lastResponse?.structured_data?.chart || null;

  const chartTitle = useMemo(() => {
    if (!lastResponse?.structured_data) {
      return "Projected Trend";
    }

    const kind = lastResponse.structured_data.kind;
    const region = lastResponse.structured_data.region_id || regionId;

    if (kind === "simulate") {
      return `Simulation · ${region}`;
    }
    if (kind === "forecast") {
      return `Forecast · ${region}`;
    }
    return `Trend · ${region}`;
  }, [lastResponse, regionId]);

  const appendMessage = (
    role: "user" | "assistant",
    text: string,
    hint?: string,
  ) => {
    setMessages((prev) => [
      ...prev,
      { id: Date.now() + prev.length, role, text, hint },
    ]);
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = query.trim();

    if (!trimmed || isLoading) {
      return;
    }

    appendMessage("user", trimmed, `Region ${regionId} | ${sliderSummary}`);
    setQuery("");
    setLastError(null);
    setIsLoading(true);

    const existingSessionId = getSessionId();
    const payload: QueryRequest = {
      query: trimmed,
      region_id: regionId,
      intervention: {
        mobility_reduction: mobilityReduction,
        vaccination_increase: vaccinationIncrease,
      },
      session_id: existingSessionId || undefined,
    };

    try {
      const { data, trace } = await runTracedEndpoint<QueryResponse>(
        "/query",
        payload,
        "chat",
      );

      setLastTraceMeta({
        latencyMs: trace.latency_ms,
        status: trace.status,
        ok: trace.ok,
      });

      if (!data) {
        const errorText = trace.error_message || "Query failed at gateway.";
        setLastError(errorText);
        appendMessage("assistant", `I hit an API error: ${errorText}`);
        return;
      }

      setLastResponse(data);
      if (data.session_id) {
        setSessionId(data.session_id);
      }

      appendMessage(
        "assistant",
        normalizeAnswer(data),
        data.followup
          ? `Follow-up requested: ${data.followup.missing_fields.join(", ") || "additional details"}`
          : undefined,
      );
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      setLastError(message);
      appendMessage("assistant", `I hit an API error: ${message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const resetChatSession = () => {
    clearSessionId();
    setLastResponse(null);
    setLastTraceMeta(null);
    setLastError(null);
    setMessages([
      {
        id: Date.now(),
        role: "assistant",
        text: "Session reset complete. Ask a fresh question whenever you are ready.",
      },
    ]);
  };

  const applyQuickPrompt = (prompt: string) => {
    setQuery(prompt);
  };

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_0%_0%,#f4ffe5_0%,#d4f4e6_30%,#f8f5ec_68%,#f7ebdc_100%)] px-4 py-8 sm:px-6 lg:px-10">
      <section className="mx-auto max-w-6xl rounded-3xl border border-emerald-200/70 bg-white/90 p-5 shadow-[0_20px_80px_rgba(16,76,52,0.14)] backdrop-blur sm:p-7">
        <header className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.26em] text-emerald-700">
              Dedicated Chat Route
            </p>
            <h1 className="mt-2 text-3xl font-bold tracking-tight text-slate-900 [font-family:Space_Grotesk,ui-sans-serif,system-ui] sm:text-4xl">
              Immersive Agent Chat
            </h1>
            <p className="mt-3 max-w-2xl text-sm text-slate-600">
              Drive region-level forecasting and intervention logic through one
              focused workspace with live verification and execution traces.
            </p>
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={resetChatSession}
              className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
            >
              Reset Session
            </button>
            <Link
              href="/"
              className="inline-flex items-center rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm font-semibold text-emerald-800 transition hover:bg-emerald-100"
            >
              Back to Dashboard
            </Link>
          </div>
        </header>

        <div className="mt-6 grid gap-4 lg:grid-cols-[minmax(0,1fr)_340px]">
          <article className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="mb-4 grid gap-3 sm:grid-cols-3">
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

            <p className="mb-4 text-xs text-slate-600">
              Intervention profile: {sliderSummary}
            </p>

            <ChatPanel
              messages={messages}
              query={query}
              isLoading={isLoading}
              quickPrompts={QUICK_PROMPTS}
              onQuickPrompt={applyQuickPrompt}
              onQueryChange={setQuery}
              onSubmit={handleSubmit}
            />

            <div className="mt-5">
              <ForecastChart
                chart={chartPayload}
                title={chartTitle}
                emptyMessage="Forecast and simulation responses will render trend charts here."
              />
            </div>
          </article>

          <aside>
            <ExplanationPanel
              response={lastResponse}
              traceMeta={lastTraceMeta}
              lastError={lastError}
            />
          </aside>
        </div>
      </section>
    </main>
  );
}
