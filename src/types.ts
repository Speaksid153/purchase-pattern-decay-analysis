export type RiskTier = 'High' | 'Medium' | 'Low';
export type CustomerFilter = 'Review' | 'All' | RiskTier;

export interface CustomerResponse {
  customers: Customer[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

export interface Customer {
  id: string;
  riskScore: number;
  riskTier: RiskTier;
  lastPurchaseDays: number;
  lastPurchaseDate: string;
  historicAvgGap: number;
  orderVolume: number;
  primaryRiskDriver: {
    feature: string;
    category?: string;
    shapValue?: number;
  };
  protectiveFactor: {
    feature: string;
    category?: string;
    shapValue?: number;
  };
  timelineHistory: {
    day: number;
    score: number;
  }[];
  notes?: string;
  // Backend detailed fields (present only in full profile responses)
  shapDrivers?: {
    feature: string;
    cleanDescription: string;
    category: string;
    shapValue: number;
    suggestedAction: string;
  }[];
  insightReport?: {
    risk_summary?: string;
    behavioral_interpretation?: string;
  };
  recommendedIntervention?: string;
  orderHistory?: {
    orderNumber: number;
    daysSincePrior: number | null;
  }[];
}

export interface PortfolioSummary {
  highRiskCount: number;
  mediumRiskCount: number;
  lowRiskCount: number;
  totalCustomers: number;
  elevatedRiskPercentage: number;
  primaryBehavioralSignal: string;
  portfolioInsightHeadline: string;
  portfolioInsightBody: string;
}

export interface ModelMetrics {
  modelName: string;
  rocAuc: number;
  prAuc: number;
  evaluationThreshold: number;
  precisionAtEvaluationThreshold: number;
  recallAtEvaluationThreshold: number;
  medianLeadTimeDays: number;
  correctlyFlaggedUsers: number;
  positiveEventUsers: number;
  methodology: string;
}
