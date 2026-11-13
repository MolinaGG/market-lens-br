export type SeriesInfo = {
  series_id: string;
  name: string;
  unit: string;
  source_url: string;
  observation_count: number;
  start_date: string;
  end_date: string;
  cash_flow_count: number;
  frequency: "daily" | "monthly";
  source_rights: string;
};

export type Catalog = {
  version: string;
  fetched_at: string;
  instruments: SeriesInfo[];
  factors: SeriesInfo[];
  default_instrument_id: string;
  benchmark_id: string;
};

export type Series = {
  version: string;
  series: SeriesInfo;
  observations: { date: string; value: number; source_url: string }[];
  cash_flows: { date: string; amount: number; source_url: string }[];
};

export type ReturnPoint = {
  date: string;
  price_return: number;
  total_return: number;
  factor_changes: Record<string, number>;
};

export type RegressionFit = {
  coefficients: Record<string, number>;
  confidence_intervals: Record<string, [number, number]>;
  r_squared: number;
  train_rmse: number;
  holdout_rmse: number;
  sample_dates: string[];
  train_count: number;
  holdout_count: number;
};

export type Regression = {
  version: string;
  instrument_id: string;
  factor_ids: string[];
  train_end: string;
  price: RegressionFit;
  total: RegressionFit;
  points: ReturnPoint[];
  adjustment_convention: string;
  source_urls: string[];
};

export type EventWindow = {
  horizon: number;
  session_dates: string[];
  observed_return: number | null;
  benchmark_return: number | null;
  abnormal_return: number | null;
  reason: string | null;
  available: boolean;
};

export type MarketEvent = {
  event_id: string;
  title: string;
  source_url: string;
  published_at: string;
  publication_time_known: boolean;
  observed_at: string;
  effective_session: string | null;
  windows: Record<string, EventWindow>;
};

export type Events = {
  version: string;
  topic: string;
  instrument_id: string;
  benchmark_id: string;
  events: MarketEvent[];
  cohort: Record<string, {
    horizon: number;
    sample_count: number;
    excluded_overlap: number;
    mean_abnormal_return: number | null;
    confidence_interval: [number, number] | null;
  }>;
  method_note: string;
};

export type CompanyFiling = {
  filing_id: string;
  ticker: string;
  company_code: string;
  category: string;
  title: string;
  status: "active" | "refiled" | "cancelled";
  published_at: string;
  publication_time_known: boolean;
  reference_date: string;
  protocol: string;
  version: number;
  source_url: string;
  source_dataset_url: string;
  fetched_at: string;
  source_rights: string;
  impact_eligible: boolean;
};

export type NewsItem = {
  ticker: string;
  title: string;
  source_url: string;
  domain: string;
  language: string;
  seen_at: string;
  published_at: string | null;
  publication_time_known: boolean;
  fetched_at: string;
  metadata_source_url: string;
  source_rights: string;
};

export type CompanyNews = {
  version: string;
  fetched_at: string;
  ticker: string;
  company_code: string;
  filings: CompanyFiling[];
  articles: NewsItem[];
  method_note: string;
};

export type FilingImpact = {
  filing_id: string;
  title: string;
  category: string;
  status: string;
  source_url: string;
  published_at: string;
  effective_session: string | null;
  train_count: number;
  coefficients: Record<string, number> | null;
  reason: string | null;
  windows: Record<string, EventWindow>;
};

export type LocalNewsImpact = {
  version: string;
  ticker: string;
  factor_ids: string[];
  events: FilingImpact[];
  cohort: Events["cohort"];
  method_note: string;
};
