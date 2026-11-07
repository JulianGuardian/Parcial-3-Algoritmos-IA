import { screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { renderWithTheme } from '../../../testUtils'
import { EmptyConversationState } from './EmptyConversationState'

describe('EmptyConversationState', () => {
  it('introduces the Nubara flight assistant and invites a question about a flight change', () => {
    renderWithTheme(<EmptyConversationState />)

    expect(screen.getByText('Nubara flight assistant')).toBeInTheDocument()
    expect(screen.getByText(/Ask me about a change to your flight/)).toBeInTheDocument()
  })

  it('shows the assistant avatar', () => {
    const { container } = renderWithTheme(<EmptyConversationState />)

    expect(container.querySelector('svg')).toBeInTheDocument()
  })
})
