export interface Token {
  access_token: string;
  token_type: string;
}

export interface UserContext {
  conditions?: Array<{
    name: string;
    parameters?: Record<string, any>;
  }>;
  medications?: Array<{
    generic_name: string;
    dose?: string;
    frequency?: string;
    timing?: string;
  }>;
  allergies?: string[];
  dietary_preferences?: string[];
  food_preferences?: string[];
  demographics?: {
    age?: number;
    sex?: string;
    lifestyle_notes?: string;
  };
  [key: string]: any;
}

export interface ChatRequest {
  message: string;
  user_context: UserContext;
}

export interface NLPParseRequest {
  message: string;
}

export interface SimulationRequest {
  user_context: UserContext;
  food_id: string;
}

export interface RecommendationResult {
  food_id: string;
  classification: string;
  explanation?: string | null;
  score?: {
    food_id: string;
    nutrition_score: number;
    condition_compatibility: number;
    medication_safety: number;
    final_score: number;
  };
  fired_rules?: Array<{
    rule_id: string;
    action: string;
    rationale: string;
  }>;
  interactions?: Array<{
    medication_id: string;
    medication_name: string;
    interaction_type: string;
    severity: string;
    mechanism: string;
    recommendation: string;
    timing_window: string;
  }>;
  food_name?: string;
  reason?: string;
  requires_professional_review?: boolean;
}

export interface ChatResponse {
  intent: string;
  nlp_provider?: string;
  deterministic_result?: RecommendationResult | any;
  explanation?: string;
  clarification_required: boolean;
  question?: string;
}

export interface Rule {
  rule_id: string;
  rule_code: string;
  rule_status: string;
  rule_version: number;
  description?: string;
  clinical_rationale?: string;
}
