import type { DisruptionDecision } from '../modules/chat/types'
import type { AgentResponse } from './types'

/**
 * Turns an agent response into the card's view model. Only passenger-visible fields cross over:
 * rule ids, the tool trajectory and the reply-fallback reason are dropped here.
 */
export function toDecisionView(response: AgentResponse): DisruptionDecision {
  const option = response.options[0] ?? null

  return {
    assessment: {
      segments: response.segments.map((segment) => ({
        segment_id: segment.segment_id,
        flight_number: segment.flight_number,
        origin: segment.origin,
        destination: segment.destination,
        status: segment.status,
        delay_minutes: segment.delay_minutes,
        estimated_departure: segment.estimated_departure,
        missed_connection: segment.missed_connection,
      })),
    },
    decision: {
      applied_rules: response.entitlements.map((item) => ({ entitlement: item.entitlement })),
      recommended_option: option
        ? {
            option_id: option.option_id,
            flight_number: option.flight_number,
            origin: option.origin,
            destination: option.destination,
            date: option.date,
            departure: option.departure,
            fare_difference: option.fare_difference,
          }
        : null,
      requires_human: response.human_required,
      human_reasons: response.human_reasons,
      policy_ref: response.policy_refs[0] ?? null,
    },
    actions: {
      human_case: response.human_case_id ? { case_id: response.human_case_id } : null,
    },
    next_step: response.next_step,
    degraded: response.degraded,
  }
}
