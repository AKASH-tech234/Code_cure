export type Followup = {
  question: string;
  missing_fields: string[];
};

export type ChartSeries = {
  name: string;
  values: number[];
};

export type ChartPayload = {
  chart_type: "line";
  x_axis_label?: string;
  y_axis_label?: string;
  labels: string[];
  series: ChartSeries[];
  summary?: {
    delta_cases?: number | null;
  };
};

export type StructuredData = {
  kind: "forecast" | "simulate" | "risk" | "rag";
  region_id?: string;
  risk_score?: number;
  risk_level?: string;
  growth_rate?: number;
  predicted_cases?: number[];
  horizon_days?: number;
  as_of_date?: string;
  baseline_cases?: number[];
  simulated_cases?: number[];
  delta_cases?: number;
  impact_summary?: string;
  drivers?: Array<{ factor: string; value: number; weight: number }>;
  source_count?: number;
  has_context?: boolean;
  chart?: ChartPayload;
};

export type QueryRequest = {
  query: string;
  session_id?: string;
  region_id?: string;
  intervention?: {
    mobility_reduction: number;
    vaccination_increase: number;
  };
};

export type QueryResponse = {
  session_id: string;
  answer: string | null;
  intent: string | null;
  tool: string | null;
  reasoning: string | null;
  sources: string[];
  structured_data: StructuredData | null;
  followup: Followup | null;
};

export type ForecastResponse = {
  region_id: string;
  predicted_cases: number[];
  growth_rate: number;
  risk_score: number;
  risk_level: string;
  horizon_days: number;
  as_of_date: string;
};

export type SimulateResponse = {
  region_id: string;
  baseline_cases: number[];
  simulated_cases: number[];
  delta_cases: number;
  impact_summary: string;
};

export type RiskResponse = {
  region_id: string;
  risk_level: string;
  risk_score: number;
  drivers: Array<{
    factor: string;
    value: number;
    weight: number;
  }>;
};

export type GatewayEndpoint = "/forecast" | "/simulate" | "/risk" | "/query";

export type ApiTraceSource =
  | "manual-console"
  | "run-all"
  | "chat"
  | "controls"
  | "replay";

export type ApiTrace = {
  id: string;
  endpoint: GatewayEndpoint;
  source: ApiTraceSource;
  timestamp: string;
  latency_ms: number;
  status: number | null;
  ok: boolean;
  error_message?: string;
  request_body: unknown;
  response_body: unknown;
};

export type TracedApiResult<T> = {
  data: T | null;
  trace: ApiTrace;
};
