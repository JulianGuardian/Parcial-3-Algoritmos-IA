import type { NextStep } from '../../api/types'

// UI view model of the trip-update card. The connected chat fills it from the agent response
// (POST /api/v1/conversations/{id}/messages) through `api/mapper.ts`; the sample fixtures follow
// the same shape.
//
// Names and nesting follow the API (snake_case) so a later change can pass the
// response through with little mapping. Only what the passenger may see is
// declared: discarded events, rejected options, rule identifiers, option
// confidence and the trace do not exist here, so a component cannot render
// them and a fixture cannot contain them without a type error.

export type MessageRole = 'user' | 'assistant' | 'system'

export interface SegmentSummary {
  segment_id: string
  flight_number: string
  origin: string
  destination: string
  /** Backend status code: SCHEDULED, ON_TIME, DELAYED, CANCELLED, CONFLICTING or UNVERIFIED. */
  status: string
  delay_minutes: number
  /** Airport-local ISO time such as 2026-09-15T17:10:00, shown as given. */
  estimated_departure: string | null
  missed_connection: boolean
}

export interface AppliedRule {
  entitlement: string
}

export interface RecommendedOption {
  /** Needed to confirm the option; absent in the sample fixtures. */
  option_id?: string
  flight_number: string | null
  origin: string | null
  destination: string | null
  /** YYYY-MM-DD. */
  date: string | null
  /** HH:MM, airport-local. */
  departure: string | null
  fare_difference: number | null
}

export interface DisruptionDecision {
  assessment: {
    segments: SegmentSummary[]
  }
  decision: {
    applied_rules: AppliedRule[]
    recommended_option: RecommendedOption | null
    requires_human: boolean
    human_reasons: string[]
    policy_ref: string | null
  }
  actions: {
    human_case: { case_id: string } | null
  }
  /** What the passenger should expect next; absent in the sample fixtures. */
  next_step?: NextStep | null
  /** True when the standard (non-AI) answer was used because the assistant model was unavailable. */
  degraded?: boolean
}

export interface Message {
  id: string
  role: MessageRole
  /** Plain text: for assistant messages this is the notification text of the response. */
  content: string
  decision?: DisruptionDecision | null
}
