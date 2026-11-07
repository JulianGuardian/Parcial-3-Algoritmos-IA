import type { CSSProperties } from 'react'

export interface IconProps {
  className?: string
  style?: CSSProperties
  /** Accessible name. Without it the icon is decorative and hidden from assistive technology. */
  title?: string
}

/** ARIA attributes for an icon: a named image when it has a title, otherwise decorative. */
export function iconA11y(title?: string) {
  return title ? { role: 'img' as const, 'aria-label': title } : { 'aria-hidden': true as const }
}
