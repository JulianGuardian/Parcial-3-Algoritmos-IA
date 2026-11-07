// Times and dates from the backend are airport-local and are shown as given.
// These helpers read the text and never build a Date, so the browser's time
// zone cannot shift what the passenger sees.

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

/** `2026-09-15T17:10:00` or `17:10` -> `17:10`; null when there is no time. */
export function formatClock(value: string | null | undefined): string | null {
  const match = value?.match(/(?:^|T)(\d{2}:\d{2})/)
  return match ? match[1] : null
}

/** `2026-09-16` -> `16 Sep 2026`; null when the text is not a date. */
export function formatDate(value: string | null | undefined): string | null {
  const match = value?.match(/^(\d{4})-(\d{2})-(\d{2})/)
  if (!match) {
    return null
  }
  const month = MONTHS[Number(match[2]) - 1]
  return month ? `${Number(match[3])} ${month} ${match[1]}` : null
}
