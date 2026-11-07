import type { Message } from './types'

// Temporary example data so every message and card state can be reviewed without a backend.
// Values follow the response of POST /api/v1/disruptions/{booking_id}/resolve (booking ABC123 and
// variants) and contain only passenger-visible fields. Remove together with the seeding in App.tsx
// when the chat is connected to the API.
export const sampleMessages: Message[] = [
  {
    id: 'sample-1',
    role: 'user',
    content: 'What happened to my flight?',
  },
  {
    id: 'sample-2',
    role: 'assistant',
    content:
      'Hello María. Your flight NB500 from SCL to LIM is delayed by 160 minutes (new departure 17:10). ' +
      'Because of this you will miss your connection NB2410 from LIM to MEX. ' +
      'We can offer you flight NB2412 from LIM to MEX on 2026-09-16 at 08:15 at no extra cost. ' +
      'An agent will contact you to confirm this option before any change is made. ' +
      'Policy reference: POL-DELAY-2026-03.',
    decision: {
      assessment: {
        segments: [
          {
            segment_id: 'S1',
            flight_number: 'NB500',
            origin: 'SCL',
            destination: 'LIM',
            status: 'DELAYED',
            delay_minutes: 160,
            estimated_departure: '2026-09-15T17:10:00',
            missed_connection: false,
          },
          {
            segment_id: 'S2',
            flight_number: 'NB2410',
            origin: 'LIM',
            destination: 'MEX',
            status: 'SCHEDULED',
            delay_minutes: 0,
            estimated_departure: '2026-09-15T19:05:00',
            missed_connection: true,
          },
        ],
      },
      decision: {
        applied_rules: [{ entitlement: 'REBOOK_NO_FEE' }, { entitlement: 'PRIORITY_HANDLING' }],
        recommended_option: {
          flight_number: 'NB2412',
          origin: 'LIM',
          destination: 'MEX',
          date: '2026-09-16',
          departure: '08:15',
          fare_difference: 0,
        },
        requires_human: true,
        human_reasons: ['R5_PRIORITY_HANDLING'],
        policy_ref: 'POL-DELAY-2026-03',
      },
      actions: { human_case: { case_id: 'HC-90412' } },
    },
  },
  {
    id: 'sample-3',
    role: 'user',
    content: 'Can I ask for compensation?',
  },
  {
    id: 'sample-4',
    role: 'assistant',
    content:
      'Hello María. Your flight NB500 from SCL to LIM is delayed by 160 minutes (new departure 17:10). ' +
      'We can offer you flight NB2412 from LIM to MEX on 2026-09-16 at 08:15 at no extra cost. ' +
      'An agent will review your compensation request. ' +
      'An agent will contact you to confirm this option before any change is made. ' +
      'Policy reference: POL-DELAY-2026-03.',
    decision: {
      assessment: {
        segments: [
          {
            segment_id: 'S1',
            flight_number: 'NB500',
            origin: 'SCL',
            destination: 'LIM',
            status: 'DELAYED',
            delay_minutes: 160,
            estimated_departure: '2026-09-15T17:10:00',
            missed_connection: false,
          },
        ],
      },
      decision: {
        applied_rules: [
          { entitlement: 'REBOOK_NO_FEE' },
          { entitlement: 'CASH_COMPENSATION' },
          { entitlement: 'PRIORITY_HANDLING' },
        ],
        recommended_option: {
          flight_number: 'NB2412',
          origin: 'LIM',
          destination: 'MEX',
          date: '2026-09-16',
          departure: '08:15',
          fare_difference: 0,
        },
        requires_human: true,
        human_reasons: ['R4_CASH_COMPENSATION', 'R5_PRIORITY_HANDLING'],
        policy_ref: 'POL-DELAY-2026-03',
      },
      actions: { human_case: { case_id: 'HC-90413' } },
    },
  },
  {
    id: 'sample-5',
    role: 'assistant',
    content:
      'Hello Ana. Your flight NB301 from SCL to EZE was cancelled. ' +
      'We can offer you flight NB303 from SCL to EZE on 2026-09-15 at 18:40 at no extra cost. ' +
      'We have requested this change; you will receive a confirmation once it is completed. ' +
      'Policy reference: POL-DELAY-2026-03.',
    decision: {
      assessment: {
        segments: [
          {
            segment_id: 'S1',
            flight_number: 'NB301',
            origin: 'SCL',
            destination: 'EZE',
            status: 'CANCELLED',
            delay_minutes: 0,
            estimated_departure: null,
            missed_connection: false,
          },
        ],
      },
      decision: {
        applied_rules: [{ entitlement: 'REBOOK_NO_FEE' }],
        recommended_option: {
          flight_number: 'NB303',
          origin: 'SCL',
          destination: 'EZE',
          date: '2026-09-15',
          departure: '18:40',
          fare_difference: 0,
        },
        requires_human: false,
        human_reasons: [],
        policy_ref: 'POL-DELAY-2026-03',
      },
      actions: { human_case: null },
    },
  },
  {
    id: 'sample-6',
    role: 'assistant',
    content: 'Hello Luis. We are still confirming the latest status of your trip. An agent will contact you with your options.',
    decision: {
      assessment: {
        segments: [
          {
            segment_id: 'S1',
            flight_number: 'NB820',
            origin: 'SCL',
            destination: 'LIM',
            status: 'UNVERIFIED',
            delay_minutes: 0,
            estimated_departure: null,
            missed_connection: false,
          },
        ],
      },
      decision: {
        applied_rules: [],
        recommended_option: null,
        requires_human: true,
        human_reasons: ['ASSESSMENT_UNVERIFIED'],
        policy_ref: null,
      },
      actions: { human_case: { case_id: 'HC-90414' } },
    },
  },
  {
    id: 'sample-7',
    role: 'assistant',
    content: 'Hello Eva. There are no changes to your trip that require action.',
  },
]
