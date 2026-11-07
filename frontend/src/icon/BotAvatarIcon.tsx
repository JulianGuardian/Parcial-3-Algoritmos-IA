import { iconA11y } from './IconProps'
import type { IconProps } from './IconProps'

export function BotAvatarIcon({ className, style, title }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={className} style={style} {...iconA11y(title)}>
      <rect x="6" y="8" width="12" height="9" rx="3" stroke="currentColor" strokeWidth="1.7" />
      <path d="M12 5.5V8" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
      <circle cx="10" cy="12.5" r="0.85" fill="currentColor" />
      <circle cx="14" cy="12.5" r="0.85" fill="currentColor" />
      <path d="M10 15H14" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
    </svg>
  )
}
