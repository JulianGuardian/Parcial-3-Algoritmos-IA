import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { BotAvatarIcon } from './BotAvatarIcon'
import { UserAvatarIcon } from './UserAvatarIcon'

describe.each([
  ['BotAvatarIcon', BotAvatarIcon, 'Assistant'],
  ['UserAvatarIcon', UserAvatarIcon, 'You'],
])('%s', (_name, Icon, title) => {
  it('is decorative when it has no title', () => {
    const { container } = render(<Icon />)

    const svg = container.querySelector('svg')
    expect(svg).toBeInTheDocument()
    expect(svg).toHaveAttribute('aria-hidden', 'true')
    expect(svg).not.toHaveAttribute('role')
  })

  it('has an accessible name when it has a title', () => {
    render(<Icon title={title} />)

    expect(screen.getByRole('img', { name: title })).toBeInTheDocument()
  })

  it('forwards className and style', () => {
    const { container } = render(<Icon className="avatar" style={{ width: 16 }} />)

    const svg = container.querySelector('svg')
    expect(svg).toHaveClass('avatar')
    expect(svg).toHaveStyle({ width: '16px' })
  })
})
