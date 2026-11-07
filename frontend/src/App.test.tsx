import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import App from './App'
import { renderWithTheme } from './testUtils'

beforeEach(() => {
  Element.prototype.scrollIntoView = vi.fn()
})

describe('App', () => {
  it('renders the chat page as the root page, with the messages area and the composer', () => {
    renderWithTheme(<App />)

    expect(screen.getByRole('log', { name: 'Conversation' })).toBeInTheDocument()
    expect(screen.getByRole('textbox', { name: 'Your question' })).toBeInTheDocument()
  })

  it('starts with the example conversation, including a decision card', () => {
    renderWithTheme(<App />)

    expect(screen.getByText('What happened to my flight?', { selector: 'p' })).toBeInTheDocument()
    expect(screen.getAllByRole('region', { name: 'Your trip update' }).length).toBeGreaterThan(0)
  })

  it('appends the passenger message when a question is sent', async () => {
    const user = userEvent.setup({ delay: null })
    renderWithTheme(<App />)

    await user.type(screen.getByRole('textbox', { name: 'Your question' }), 'Will I get a meal voucher?{Enter}')

    const sent = screen.getByText('Will I get a meal voucher?')
    expect(sent.closest('[role="article"]')).toHaveAccessibleName('Your message')
  })
})
