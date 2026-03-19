export interface ExecutiveSummary {
  recent_call: string;
  past_6_months_calls: number;
  call_frequency: string;
  co_calling_rep: string;
  call_fatigue_risk: boolean;
  risk_note: string;
}

export interface ControlLimits {
  ucl: number;
  center: number;
  lcl: number;
}

export interface DupixentAsthma {
  december_2025: number;
  "24_month_average": number;
  control_limits: ControlLimits;
  trend: string;
}

export interface XolairCompetitiveThreat {
  december_2025: number;
  average: number;
  ucl: number;
  status: string;
  spike_percentage: string;
  note: string;
}

export interface LabaIcsBaseline {
  december_2025: number;
  average: number;
  note: string;
}

export interface PrescribingTrends {
  dupixent_asthma: DupixentAsthma;
  xolair_competitive_threat: XolairCompetitiveThreat;
  laba_ics_baseline: LabaIcsBaseline;
}

export interface PullThroughFailures {
  count: number;
  description: string;
  root_cause: string;
}

export interface PersistenceRisk {
  count: number;
  description: string;
  risk: string;
}

export interface UntappedOpportunity {
  count: number;
  description: string;
  growth_trend: string;
  profile: string;
}

export interface CopdExpansion {
  count: number;
  description: string;
}

export interface SmartAlerts {
  total_alerts_90_days: number;
  pull_through_failures: PullThroughFailures;
  persistence_risk: PersistenceRisk;
  untapped_opportunity: UntappedOpportunity;
  copd_expansion: CopdExpansion;
}

export interface RecommendedApproachStep {
  step: number;
  title: string;
  message: string;
  key_question?: string;
  key_questions?: string[];
  resources?: string[];
}

export interface KeyCommitment {
  commitment: string;
  ask: string;
}

export interface ObjectionHandling {
  objection: string;
  response: string;
}

export interface RolePlayQA {
  question: string;
  answer: string;
}

export interface Challenge {
  challenge: string;
  description: string;
}

export interface StrategicSummary {
  good_news: string[];
  challenges: Challenge[];
  action_plan: string[];
  bottom_line: string;
}

export interface PreCallPlan {
  hcp_id: string;
  hcp_name: string;
  call_date: string;
  specialty: string;
  segment: string;
  brand_focus: string;
  executive_summary: ExecutiveSummary;
  prescribing_trends: PrescribingTrends;
  smart_alerts: SmartAlerts;
  primary_objective: string;
  critical_insight: string;
  recommended_approach: RecommendedApproachStep[];
  key_commitments: KeyCommitment[];
  objection_handling: ObjectionHandling[];
  role_play_qa: RolePlayQA[];
  resources_to_bring: string[];
  strategic_summary: StrategicSummary;
}
