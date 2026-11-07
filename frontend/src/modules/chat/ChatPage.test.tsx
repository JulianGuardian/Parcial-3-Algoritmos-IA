import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { renderWithTheme } from '../../testUtils'
import { ChatPage } from './ChatPage'
import { sampleMessages } from './fixtures'
import type { Message } from './types'

const scrollIntoView = vi.fn()

beforeEach(() => {
  scrollIntoView.mockReset()
  Element.prototype.scrollIntoView = scrollIntoView
})

afterEach(() => {
  Reflect.deleteProperty(Element.prototype, 'scrollIntoView')
  vi.unstubAllGlobals()
})

function message(id: string, role: Message['role'] = 'assistant', content = `Message ${id}`): Message {
  return { id, role, content }
}

function emittedCss() {
  return Array.from(document.querySelectorAll('style'))
    .map((style) => style.textContent)
    .join('')
}

const welcome = /Ask me about a change to your flight/

describe('ChatPage layout', () => {
  it('puts the messages area above the composer inside one bordered container', () => {
    renderWithTheme(<ChatPage messages={[message('1')]} onSubmit={vi.fn()} />)

    const log = screen.getByRole('log', { name: 'Conversation' })
    const input = screen.getByRole('textbox', { name: 'Your question' })
    const container = log.parentElement as HTMLElement

    expect(container).toHaveClass('MuiPaper-root')
    expect(container).toContainElement(input)
    expect(log.compareDocumentPosition(input) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  })

  it('scrolls only the messages area when the content is long', () => {
    renderWithTheme(<ChatPage messages={[message('1')]} onSubmit={vi.fn()} />)

    const log = screen.getByRole('log', { name: 'Conversation' })
    expect(log).toHaveStyle({ overflowY: 'auto' })
    expect(log.parentElement).toHaveStyle({ overflow: 'hidden' })
  })

  it('uses compact padding on narrow screens and wider padding from the medium breakpoint', () => {
    renderWithTheme(<ChatPage messages={[]} onSubmit={vi.fn()} />)

    expect(emittedCss()).toMatch(/padding-left:\s*16px/)
    expect(emittedCss()).toMatch(/@media \(min-width:\s*900px\)\s*\{[\s\S]*?padding-left:\s*32px/)
  })
})

describe('ChatPage states', () => {
  it('shows the welcome message when there are no messages', () => {
    renderWithTheme(<ChatPage messages={[]} onSubmit={vi.fn()} />)

    expect(screen.getByText(welcome)).toBeInTheDocument()
  })

  it('stops showing the welcome message once there is a message', () => {
    const { rerender } = renderWithTheme(<ChatPage messages={[]} onSubmit={vi.fn()} />)
    expect(screen.getByText(welcome)).toBeInTheDocument()

    rerender(<ChatPage messages={[message('1', 'user', 'Hello')]} onSubmit={vi.fn()} />)

    expect(screen.queryByText(welcome)).not.toBeInTheDocument()
    expect(screen.getByText('Hello')).toBeInTheDocument()
  })

  it('shows the loading text instead of messages and the welcome message', () => {
    renderWithTheme(<ChatPage messages={[message('1')]} isLoading onSubmit={vi.fn()} />)

    expect(screen.getByText('Loading conversation...')).toBeInTheDocument()
    expect(screen.queryByText('Message 1')).not.toBeInTheDocument()
    expect(screen.queryByText(welcome)).not.toBeInTheDocument()
  })

  it('shows the error banner above the container when there is an error', () => {
    renderWithTheme(<ChatPage messages={[]} error="Could not load the conversation." onSubmit={vi.fn()} />)

    const banner = screen.getByRole('alert')
    const container = screen.getByRole('log').parentElement as HTMLElement
    expect(banner).toHaveTextContent('Could not load the conversation.')
    expect(banner.compareDocumentPosition(container) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  })

  it('shows no banner without an error', () => {
    renderWithTheme(<ChatPage messages={[]} onSubmit={vi.fn()} />)

    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('disables the composer while submitting', () => {
    renderWithTheme(<ChatPage messages={[]} isSubmitting onSubmit={vi.fn()} />)

    expect(screen.getByRole('textbox', { name: 'Your question' })).toBeDisabled()
  })

  it('shows a decision card for an assistant message that has a decision', () => {
    renderWithTheme(<ChatPage messages={sampleMessages.slice(0, 2)} onSubmit={vi.fn()} />)

    expect(screen.getByRole('region', { name: 'Your trip update' })).toBeInTheDocument()
  })
})

describe('ChatPage latest message', () => {
  it('ends the messages with a 1px marker, not a full-height blank block', () => {
    renderWithTheme(<ChatPage messages={[message('1')]} onSubmit={vi.fn()} />)

    const marker = screen.getByRole('log').lastElementChild as HTMLElement
    expect(marker).toHaveStyle({ height: '1px' })
  })

  it('jumps to the last message without animation when messages are first shown', () => {
    renderWithTheme(<ChatPage messages={[message('1'), message('2')]} onSubmit={vi.fn()} />)

    expect(scrollIntoView).toHaveBeenCalledTimes(1)
    expect(scrollIntoView).toHaveBeenCalledWith({ behavior: 'instant', block: 'end' })
  })

  it('scrolls smoothly when a message is appended', () => {
    const { rerender } = renderWithTheme(<ChatPage messages={[message('1')]} onSubmit={vi.fn()} />)
    scrollIntoView.mockClear()

    rerender(<ChatPage messages={[message('1'), message('2')]} onSubmit={vi.fn()} />)

    expect(scrollIntoView).toHaveBeenCalledTimes(1)
    expect(scrollIntoView).toHaveBeenCalledWith({ behavior: 'smooth', block: 'end' })
  })

  it('does not scroll again when the last message did not change', () => {
    const { rerender } = renderWithTheme(<ChatPage messages={[message('1')]} onSubmit={vi.fn()} />)
    scrollIntoView.mockClear()

    rerender(<ChatPage messages={[message('1')]} error="Notice" onSubmit={vi.fn()} />)

    expect(scrollIntoView).not.toHaveBeenCalled()
  })

  it('waits for loading to finish before the first jump', () => {
    const { rerender } = renderWithTheme(<ChatPage messages={[]} isLoading onSubmit={vi.fn()} />)
    expect(scrollIntoView).not.toHaveBeenCalled()

    rerender(<ChatPage messages={[message('1')]} onSubmit={vi.fn()} />)

    expect(scrollIntoView).toHaveBeenCalledWith({ behavior: 'instant', block: 'end' })
  })
})

describe('ChatPage backend independence', () => {
  it('renders and handles input without sending any request', async () => {
    const fetchSpy = vi.fn()
    vi.stubGlobal('fetch', fetchSpy)
    const onSubmit = vi.fn()
    const user = userEvent.setup({ delay: null })
    renderWithTheme(<ChatPage messages={sampleMessages} onSubmit={onSubmit} />)

    await user.type(screen.getByRole('textbox', { name: 'Your question' }), 'What are my options?{Enter}')

    expect(onSubmit).toHaveBeenCalledWith('What are my options?')
    expect(fetchSpy).not.toHaveBeenCalled()
  })
})
