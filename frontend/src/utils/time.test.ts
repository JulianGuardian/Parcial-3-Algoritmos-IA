import { afterEach, describe, expect, it, vi } from 'vitest'

import { formatClock, formatDate } from './time'

describe('formatClock', () => {
  it('reads the time of an ISO local date-time', () => {
    expect(formatClock('2026-09-15T17:10:00')).toBe('17:10')
  })

  it('accepts a bare HH:MM', () => {
    expect(formatClock('08:15')).toBe('08:15')
  })

  it('ignores an offset or a zone suffix: the text is shown as given', () => {
    expect(formatClock('2026-09-15T20:35:00Z')).toBe('20:35')
  })

  it.each([null, undefined, '', 'soon'])('returns null for %s', (value) => {
    expect(formatClock(value)).toBeNull()
  })
})

describe('formatDate', () => {
  it('formats a date with a fixed month table', () => {
    expect(formatDate('2026-09-16')).toBe('16 Sep 2026')
  })

  it('drops the leading zero of the day', () => {
    expect(formatDate('2026-01-05')).toBe('5 Jan 2026')
  })

  it('accepts a date-time and keeps the date part', () => {
    expect(formatDate('2026-12-31T23:59:00')).toBe('31 Dec 2026')
  })

  it.each([null, undefined, '', 'tomorrow', '2026-13-01'])('returns null for %s', (value) => {
    expect(formatDate(value)).toBeNull()
  })
})

describe('time zone independence', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('never builds a Date, so the browser time zone cannot change the result', () => {
    const spy = vi.spyOn(globalThis, 'Date')

    formatClock('2026-09-15T17:10:00')
    formatDate('2026-09-16')

    expect(spy).not.toHaveBeenCalled()
  })
})
