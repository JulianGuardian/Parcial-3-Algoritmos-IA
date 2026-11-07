import { describe, expect, it } from 'vitest'

import { toDecisionView } from './mapper'
import { abc123Response, def456Response } from './sampleResponses'

describe('toDecisionView', () => {
  it('maps the ABC123 agent response to the card view', () => {
    const view = toDecisionView(abc123Response)

    expect(view.assessment.segments.map((s) => [s.flight_number, s.status, s.missed_connection])).toEqual([
      ['NB500', 'DELAYED', false],
      ['NB2410', 'SCHEDULED', true],
    ])
    expect(view.decision.applied_rules).toEqual([{ entitlement: 'REBOOK_NO_FEE' }, { entitlement: 'PRIORITY_HANDLING' }])
    expect(view.decision.recommended_option).toMatchObject({ option_id: 'O1', flight_number: 'NB2412', fare_difference: 0 })
    expect(view.decision.requires_human).toBe(true)
    expect(view.decision.human_reasons).toEqual(['R5_PRIORITY_HANDLING'])
    expect(view.decision.policy_ref).toBe('POL-DELAY-2026-03')
    expect(view.actions.human_case).toEqual({ case_id: 'HC-4471' })
    expect(view.next_step).toBe('AGENT_WILL_CONTACT')
  })

  it('drops rule ids, the tool trajectory and the reply-fallback reason', () => {
    const dumped = JSON.stringify(toDecisionView({ ...abc123Response, reply_fallback: 'mentions_other_option' }))

    for (const hidden of ['R3', 'R5"', 'trajectory', 'get_trip_status', 'mentions_other_option', 'rule_id']) {
      expect(dumped).not.toContain(hidden)
    }
  })

  it('has no option and no case when the response has none', () => {
    const view = toDecisionView({ ...def456Response, options: [], human_case_id: null })

    expect(view.decision.recommended_option).toBeNull()
    expect(view.actions.human_case).toBeNull()
    expect(view.degraded).toBe(true)
  })
})
