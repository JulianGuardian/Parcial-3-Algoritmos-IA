import { describe, expect, it } from 'vitest'

import { sampleMessages } from './fixtures'

const FORBIDDEN_TEXT = ['LEGACY_MIRROR', 'OPS_CORE', 'AIRPORT_FEED', '12.345.678-9', 'maria.silva@example.com']
const FORBIDDEN_KEYS = ['discarded_events', 'rejected_options', 'trace', 'rule_id', 'confidence', 'document_id']

describe('sampleMessages', () => {
  it('has unique ids', () => {
    const ids = sampleMessages.map((message) => message.id)

    expect(new Set(ids).size).toBe(ids.length)
  })

  it('covers every card state: delay, compensation, cancellation, unverified and no card', () => {
    const decisions = sampleMessages.flatMap((message) => (message.decision ? [message.decision] : []))
    const statuses = decisions.flatMap((d) => d.assessment.segments.map((s) => s.status))

    expect(statuses).toEqual(expect.arrayContaining(['DELAYED', 'CANCELLED', 'UNVERIFIED']))
    expect(decisions.some((d) => d.decision.applied_rules.some((r) => r.entitlement === 'CASH_COMPENSATION'))).toBe(true)
    expect(decisions.some((d) => !d.decision.requires_human)).toBe(true)
    expect(sampleMessages.some((m) => m.role === 'assistant' && !m.decision)).toBe(true)
  })

  it('never contains internal sources, identity data or internal keys', () => {
    const json = JSON.stringify(sampleMessages)

    for (const text of FORBIDDEN_TEXT) {
      expect(json).not.toContain(text)
    }
    for (const key of FORBIDDEN_KEYS) {
      expect(json).not.toContain(`"${key}"`)
    }
  })

  it('keeps rule identifiers out of the message text', () => {
    for (const message of sampleMessages) {
      expect(message.content).not.toMatch(/\bR[1-5]\b/)
      expect(message.content).not.toMatch(/\b[A-Z]+_[A-Z_]+\b/)
    }
  })

  it('never states that the booking was changed or promises compensation', () => {
    for (const message of sampleMessages.filter((m) => m.role === 'assistant')) {
      expect(message.content).not.toMatch(/has been changed|was changed|compensation (was|has been) approved/i)
    }
  })
})
