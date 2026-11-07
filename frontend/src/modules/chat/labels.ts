// Plain-language text for backend codes. Every lookup has a generic fallback
// so an unknown code can never reach the passenger as a raw identifier.

import type { NextStep } from '../../api/types'
import type { StatusKind } from '../../utils/theme'

const STATUS_KIND: Record<string, StatusKind> = {
  SCHEDULED: 'onSchedule',
  ON_TIME: 'onSchedule',
  DELAYED: 'delayed',
  CANCELLED: 'cancelled',
}

const STATUS_LABEL: Record<StatusKind, string> = {
  onSchedule: 'On schedule',
  delayed: 'Delayed',
  cancelled: 'Cancelled',
  confirming: 'Being confirmed',
}

const ENTITLEMENT_LABEL: Record<string, string> = {
  REBOOK_NO_FEE: 'Free rebooking',
  MEAL_VOUCHER: 'Meal voucher',
  PRIORITY_HANDLING: 'Priority handling',
  CASH_COMPENSATION: 'Compensation request: an agent will review it',
}

const HUMAN_REASON_LABEL: Record<string, string> = {
  R5_PRIORITY_HANDLING: 'Priority handling for travellers with a minor',
  R4_CASH_COMPENSATION: "Your compensation request needs an agent's review",
  ASSESSMENT_CONFLICTING: 'We are still confirming the status of your trip',
  ASSESSMENT_UNVERIFIED: 'We are still confirming the status of your trip',
  MISSING_DECISION_DATA: 'Some booking details need to be checked',
  REBOOKING_INDETERMINATE: 'We could not confirm your change request; an agent will check it',
}

const NEXT_STEP_TEXT: Record<NextStep, string> = {
  CONFIRM_OPTION: 'Confirm this option if you want us to request the change.',
  AGENT_WILL_CONTACT: 'An agent will contact you shortly.',
  REBOOKING_PENDING: 'We have requested this change. You will receive a confirmation once it is completed.',
  VERIFYING: 'We are still confirming the latest status of your trip.',
  NO_ACTION_NEEDED: 'There is nothing you need to do right now.',
}

export const UNKNOWN_ENTITLEMENT_LABEL = 'Additional benefit: an agent will give you details'
export const UNKNOWN_HUMAN_REASON_LABEL = 'An agent needs to review your case'

/** Visual kind of a status; anything unknown, conflicting or unverified is "confirming". */
export function statusKind(status: string): StatusKind {
  return STATUS_KIND[status] ?? 'confirming'
}

export function statusLabel(status: string): string {
  return STATUS_LABEL[statusKind(status)]
}

/** Delay minutes and estimated times are only shown for verified statuses. */
export function isVerifiedStatus(status: string): boolean {
  return statusKind(status) !== 'confirming'
}

export function entitlementLabel(code: string): string {
  return ENTITLEMENT_LABEL[code] ?? UNKNOWN_ENTITLEMENT_LABEL
}

export function humanReasonLabel(code: string): string {
  return HUMAN_REASON_LABEL[code] ?? UNKNOWN_HUMAN_REASON_LABEL
}

export function nextStepText(step: NextStep): string {
  return NEXT_STEP_TEXT[step]
}
