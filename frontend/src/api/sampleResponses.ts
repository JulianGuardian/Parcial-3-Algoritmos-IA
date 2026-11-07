import type { AgentResponse } from './types'

// Agent responses as the backend returns them for the evaluation bookings, used by the tests.

const segments: AgentResponse['segments'] = [
  {
    segment_id: 'S1',
    flight_number: 'NB500',
    origin: 'SCL',
    destination: 'LIM',
    status: 'DELAYED',
    delay_minutes: 160,
    scheduled_departure: '2026-09-15T14:30',
    estimated_departure: '2026-09-15T17:10',
    estimated_arrival: '2026-09-15T20:35',
    missed_connection: false,
  },
  {
    segment_id: 'S2',
    flight_number: 'NB2410',
    origin: 'LIM',
    destination: 'MEX',
    status: 'SCHEDULED',
    delay_minutes: 0,
    scheduled_departure: '2026-09-15T19:05',
    estimated_departure: '2026-09-15T19:05',
    estimated_arrival: '2026-09-15T23:40',
    missed_connection: true,
  },
]

const o1: AgentResponse['options'][number] = {
  option_id: 'O1',
  type: 'REBOOK',
  flight_number: 'NB2412',
  origin: 'LIM',
  destination: 'MEX',
  date: '2026-09-16',
  departure: '08:15',
  fare_difference: 0,
  currency: null,
}

export const abc123Response: AgentResponse = {
  what_happened: ['Your flight NB500 from SCL to LIM is delayed by 160 minutes (new departure 17:10).'],
  segments,
  human_reasons: ['R5_PRIORITY_HANDLING'],
  entitlements: [
    { rule_id: 'R3', entitlement: 'REBOOK_NO_FEE', policy_ref: 'POL-DELAY-2026-03' },
    { rule_id: 'R5', entitlement: 'PRIORITY_HANDLING', policy_ref: 'POL-DELAY-2026-03' },
  ],
  options: [o1],
  next_step: 'AGENT_WILL_CONTACT',
  policy_refs: ['POL-DELAY-2026-03'],
  human_required: true,
  human_case_id: 'HC-4471',
  rebooking_status: null,
  reply: 'Your flight NB500 is delayed by 160 minutes. An agent will confirm NB2412 with you. POL-DELAY-2026-03',
  reply_fallback: null,
  degraded: false,
  trajectory: ['get_trip_status', 'get_entitlements', 'escalate_to_human'],
}

export const def456Response: AgentResponse = {
  ...abc123Response,
  human_reasons: [],
  entitlements: [{ rule_id: 'R3', entitlement: 'REBOOK_NO_FEE', policy_ref: 'POL-DELAY-2026-03' }],
  next_step: 'CONFIRM_OPTION',
  human_required: false,
  human_case_id: null,
  reply: 'We can offer NB2412 on 2026-09-16 at 08:15 at no extra cost. Please confirm. POL-DELAY-2026-03',
  degraded: true,
  trajectory: [],
}

export const def456PendingResponse: AgentResponse = {
  ...def456Response,
  next_step: 'REBOOKING_PENDING',
  rebooking_status: 'PENDING',
  reply: 'We have requested this change; you will receive a confirmation once it is completed. POL-DELAY-2026-03',
  trajectory: ['get_entitlements', 'request_rebooking'],
}
