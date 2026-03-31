import type { QueryResponse } from "@/types/api";

type TraceMeta = {
  latencyMs: number;
  status: number | null;
  ok: boolean;
};

type ExplanationPanelProps = {
  response: QueryResponse | null;
  traceMeta: TraceMeta | null;
  lastError: string | null;
};

function prettyStepLabel(step: "planner" | "tool" | "llm"): string {
  if (step === "planner") {
    return "Planner";
  }
  if (step === "tool") {
    return "Tool";
  }
  return "LLM";
}

export default function ExplanationPanel({
  response,
  traceMeta,
  lastError,
}: ExplanationPanelProps) {
  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <h2 className="text-sm font-semibold uppercase tracking-[0.16em] text-slate-700">
          Execution Status
        </h2>
        {response ? (
          <div className="mt-3 space-y-2 text-sm text-slate-700">
            <p>
              Intent:{" "}
              <span className="font-semibold text-slate-900">
                {response.intent || "n/a"}
              </span>
            </p>
            <p>
              Tool:{" "}
              <span className="font-semibold text-slate-900">
                {response.tool || "n/a"}
              </span>
            </p>
            <p>
              Verification:{" "}
              <span className="font-semibold text-slate-900">
                {response.verification?.status || "n/a"}
              </span>
            </p>
            <p>
              Can Execute:{" "}
              <span className="font-semibold text-slate-900">
                {String(response.verification?.can_execute ?? false)}
              </span>
            </p>
            {response.reasoning ? (
              <p className="rounded-lg border border-slate-200 bg-slate-50 px-2 py-1 text-xs text-slate-700">
                {response.reasoning}
              </p>
            ) : null}
          </div>
        ) : (
          <p className="mt-3 text-sm text-slate-500">No execution yet.</p>
        )}
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <h2 className="text-sm font-semibold uppercase tracking-[0.16em] text-slate-700">
          Pipeline Steps
        </h2>
        {response?.execution_steps?.length ? (
          <div className="mt-3 space-y-2">
            {response.execution_steps.map((step) => (
              <div
                key={`${step.step}-${step.detail || "none"}`}
                className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-700"
              >
                <p className="font-semibold text-slate-900">
                  {prettyStepLabel(step.step)} · {step.status}
                </p>
                {step.detail ? <p className="mt-1">{step.detail}</p> : null}
              </div>
            ))}
          </div>
        ) : (
          <p className="mt-3 text-sm text-slate-500">
            Planner and tool diagnostics will appear here.
          </p>
        )}
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <h2 className="text-sm font-semibold uppercase tracking-[0.16em] text-slate-700">
          Trace + Sources
        </h2>
        {traceMeta ? (
          <p className="mt-3 text-sm text-slate-700">
            {traceMeta.ok ? "OK" : "ERROR"} · status{" "}
            {traceMeta.status ?? "network"} · {traceMeta.latencyMs}ms
          </p>
        ) : (
          <p className="mt-3 text-sm text-slate-500">No trace recorded.</p>
        )}

        {response?.sources?.length ? (
          <div className="mt-3 space-y-1">
            {response.sources.map((source) => (
              <p
                key={source}
                className="rounded-md border border-slate-200 bg-slate-50 px-2 py-1 text-xs text-slate-700"
              >
                {source}
              </p>
            ))}
          </div>
        ) : null}

        {lastError ? (
          <p className="mt-3 rounded-lg border border-red-200 bg-red-50 px-2 py-1 text-xs text-red-700">
            {lastError}
          </p>
        ) : null}
      </div>
    </div>
  );
}
