import type {
  ApiTrace,
  ApiTraceSource,
  ForecastResponse,
  GatewayEndpoint,
  QueryRequest,
  QueryResponse,
  RiskResponse,
  SimulateResponse,
  TracedApiResult,
} from "@/types/api";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

type ApiError = Error & {
  status?: number;
  details?: unknown;
};

function createTraceId(): string {
  return `trace_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

function nowMs(): number {
  if (typeof performance !== "undefined") {
    return performance.now();
  }
  return Date.now();
}

function parseJsonOrText(rawText: string): unknown {
  if (!rawText) {
    return null;
  }

  try {
    return JSON.parse(rawText);
  } catch {
    return rawText;
  }
}

function logTrace(trace: ApiTrace): void {
  const prefix = trace.ok ? "[API OK]" : "[API ERROR]";
  // Debug-oriented logs for hackathon demo visibility.
  console.groupCollapsed(
    `${prefix} ${trace.endpoint} · ${trace.status ?? "NETWORK"} · ${trace.latency_ms}ms`,
  );
  console.log("source", trace.source);
  console.log("timestamp", trace.timestamp);
  console.log("request", trace.request_body);
  console.log("response", trace.response_body);
  if (trace.error_message) {
    console.log("error", trace.error_message);
  }
  console.groupEnd();
}

export async function runTracedEndpoint<T>(
  endpoint: GatewayEndpoint,
  body: unknown,
  source: ApiTraceSource = "manual-console",
): Promise<TracedApiResult<T>> {
  const startedAt = nowMs();
  const timestamp = new Date().toISOString();
  let status: number | null = null;
  let ok = false;
  let responseBody: unknown = null;
  let errorMessage: string | undefined;

  try {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });

    status = response.status;
    ok = response.ok;
    const rawText = await response.text();
    responseBody = parseJsonOrText(rawText);

    if (!ok) {
      errorMessage = `Request failed (${status}) for ${endpoint}`;
    }
  } catch (error) {
    ok = false;
    errorMessage = error instanceof Error ? error.message : "Network error";
    responseBody = {
      error: {
        message: errorMessage,
      },
    };
  }

  const trace: ApiTrace = {
    id: createTraceId(),
    endpoint,
    source,
    timestamp,
    latency_ms: Math.round(nowMs() - startedAt),
    status,
    ok,
    error_message: errorMessage,
    request_body: body,
    response_body: responseBody,
  };

  logTrace(trace);

  if (!ok) {
    return {
      data: null,
      trace,
    };
  }

  return {
    data: responseBody as T,
    trace,
  };
}

async function postJson<TResponse>(
  path: string,
  body: unknown,
): Promise<TResponse> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });

  const rawText = await response.text();
  let parsed: unknown = null;

  try {
    parsed = rawText ? JSON.parse(rawText) : null;
  } catch {
    parsed = rawText;
  }

  if (!response.ok) {
    const error = new Error(
      `Request failed (${response.status}) for ${path}`,
    ) as ApiError;
    error.status = response.status;
    error.details = parsed;
    throw error;
  }

  return parsed as TResponse;
}

function normalizeForecastResponse(raw: ForecastResponse): ForecastResponse {
  const horizon = raw.horizon_days ?? 7;
  if (Array.isArray(raw.predicted_cases) && raw.predicted_cases.length > 0) {
    return raw;
  }

  const point = raw.point_forecast?.predicted_roll7_cases;
  if (typeof point === "number") {
    return {
      ...raw,
      predicted_cases: Array.from({ length: horizon }, () => Math.round(point)),
    };
  }

  return {
    ...raw,
    predicted_cases: Array.from({ length: horizon }, () => 0),
  };
}

export async function runQuery(body: QueryRequest): Promise<QueryResponse> {
  return postJson<QueryResponse>("/query", body);
}

export async function runForecast(
  regionId: string,
  horizonDays = 7,
): Promise<ForecastResponse> {
  const response = await postJson<ForecastResponse>("/forecast", {
    region_id: regionId,
    horizon_days: horizonDays,
  });
  return normalizeForecastResponse(response);
}

export async function runSimulate(
  regionId: string,
  mobilityReduction: number,
  vaccinationIncrease: number,
): Promise<SimulateResponse> {
  return postJson<SimulateResponse>("/simulate", {
    region_id: regionId,
    intervention: {
      mobility_reduction: mobilityReduction,
      vaccination_increase: vaccinationIncrease,
    },
  });
}

export async function runRisk(regionId: string): Promise<RiskResponse> {
  return postJson<RiskResponse>("/risk", {
    region_id: regionId,
  });
}
