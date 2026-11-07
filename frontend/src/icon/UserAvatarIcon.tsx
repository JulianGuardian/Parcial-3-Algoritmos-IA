import { iconA11y } from './IconProps'
import type { IconProps } from './IconProps'

export function UserAvatarIcon({ className, style, title }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={className} style={style} {...iconA11y(title)}>
      <circle cx="12" cy="9" r="3.2" stroke="currentColor" strokeWidth="1.7" />
      <path
        d="M5.5 19c.9-3.1 3.4-4.7 6.5-4.7s5.6 1.6 6.5 4.7"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
      />
    </svg>
  )
}
