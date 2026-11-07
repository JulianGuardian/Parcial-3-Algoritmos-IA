// Mirror of the conversational agent API (backend `agents/contracts.py`, `api/v1/conversations.py`).
// Only fields the UI reads are typed as required; the rest are kept optional so an additive backend
// change never breaks the client.

export type NextStep = 'CONFIRM_OPTION' | 'AGENT_WILL_CONTACT' | 'REBOOKING_PENDING' | 'VERIFYING' | 'NO_ACTION_NEEDED'

export interface ApiSegment {
  segment_id: string
  flight_number: string
  origin: string
  destination: string
  status: string
  delay_minutes: number
  scheduled_departure?: string | null
  estimated_departure: string | null
  estimated_arrival?: string | null
  missed_connection: boolean
}

export interface ApiEntitlement {
  rule_id: string
  entitlement: string
  policy_ref: string
}

export interface ApiOption {
  option_id: string
  type: string
  flight_number: string | null
  origin: string | null
  destination: string | null
  date: string | null
  departure: string | null
  fare_difference: number | null
  currency?: string | null
}

export interface AgentResponse {
  what_happened: string[]
  segments: ApiSegment[]
  human_reasons: string[]
  entitlements: ApiEntitlement[]
  options: ApiOption[]
  next_step: NextStep
  policy_refs: string[]
  human_required: boolean
  human_case_id: string | null
  rebooking_status?: string | null
  reply: string
  degraded: boolean
  // Present in the response but never rendered: internal diagnostics.
  reply_fallback?: string | null
  trajectory?: string[]
}

export interface StartConversationResponse {
  conversation_id: string
  booking_id: string
}

export interface ApiErrorBody {
  error: string
  detail: string
  request_id?: string | null
}
