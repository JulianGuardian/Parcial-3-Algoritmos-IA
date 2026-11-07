import { describe, expect, it } from 'vitest'

import {
  UNKNOWN_ENTITLEMENT_LABEL,
  UNKNOWN_HUMAN_REASON_LABEL,
  entitlementLabel,
  humanReasonLabel,
  isVerifiedStatus,
  statusKind,
  statusLabel,
} from './labels'

describe('statusLabel', () => {
  it.each([
    ['SCHEDULED', 'On schedule'],
    ['ON_TIME', 'On schedule'],
    ['DELAYED', 'Delayed'],
    ['CANCELLED', 'Cancelled'],
    ['CONFLICTING', 'Being confirmed'],
    ['UNVERIFIED', 'Being confirmed'],
  ])('maps %s to "%s"', (code, label) => {
    expect(statusLabel(code)).toBe(label)
  })

  it('treats an unknown status as being confirmed, never as the raw code', () => {
    expect(statusLabel('TELEPORTED')).toBe('Being confirmed')
    expect(statusKind('TELEPORTED')).toBe('confirming')
  })
})

describe('isVerifiedStatus', () => {
  it.each(['SCHEDULED', 'ON_TIME', 'DELAYED', 'CANCELLED'])('%s is verified', (code) => {
    expect(isVerifiedStatus(code)).toBe(true)
  })

  it.each(['CONFLICTING', 'UNVERIFIED', 'TELEPORTED'])('%s is not verified', (code) => {
    expect(isVerifiedStatus(code)).toBe(false)
  })
})

describe('entitlementLabel', () => {
  it.each([
    ['REBOOK_NO_FEE', 'Free rebooking'],
    ['MEAL_VOUCHER', 'Meal voucher'],
    ['PRIORITY_HANDLING', 'Priority handling'],
    ['CASH_COMPENSATION', 'Compensation request: an agent will review it'],
  ])('maps %s', (code, label) => {
    expect(entitlementLabel(code)).toBe(label)
  })

  it('falls back to generic text and never returns the code', () => {
    const label = entitlementLabel('UPGRADE_LOUNGE')

    expect(label).toBe(UNKNOWN_ENTITLEMENT_LABEL)
    expect(label).not.toContain('UPGRADE_LOUNGE')
  })
})

describe('humanReasonLabel', () => {
  it.each([
    ['R5_PRIORITY_HANDLING', 'Priority handling for travellers with a minor'],
    ['R4_CASH_COMPENSATION', "Your compensation request needs an agent's review"],
    ['ASSESSMENT_CONFLICTING', 'We are still confirming the status of your trip'],
    ['ASSESSMENT_UNVERIFIED', 'We are still confirming the status of your trip'],
    ['MISSING_DECISION_DATA', 'Some booking details need to be checked'],
  ])('maps %s', (code, label) => {
    expect(humanReasonLabel(code)).toBe(label)
  })

  it('falls back to generic text and never returns the code', () => {
    const label = humanReasonLabel('R9_SECRET_RULE')

    expect(label).toBe(UNKNOWN_HUMAN_REASON_LABEL)
    expect(label).not.toContain('R9')
  })
})
