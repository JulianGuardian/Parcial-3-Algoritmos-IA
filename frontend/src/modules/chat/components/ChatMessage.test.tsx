import { screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { renderWithTheme } from '../../../testUtils'
import { appPalette } from '../../../utils/theme'
import { sampleMessages } from '../fixtures'
import type { Message } from '../types'
import { ChatMessage } from './ChatMessage'

const withDecision = sampleMessages.find((message) => message.id === 'sample-2') as Message

function assistantMessage(content: string, decision: Message['decision'] = null): Message {
  return { id: 'a1', role: 'assistant', content, decision }
}

function bubbleOf(text: string) {
  return screen.getByText(text).closest('.MuiPaper-root') as HTMLElement
}

function emittedCss() {
  return Array.from(document.querySelectorAll('style'))
    .map((style) => style.textContent)
    .join('')
}

function rgb(hex: string) {
  const [r, g, b] = [1, 3, 5].map((start) => parseInt(hex.slice(start, start + 2), 16))
  return `rgb(${r}, ${g}, ${b})`
}

describe('ChatMessage alignment and avatars', () => {
  it('aligns a user message to the right with the user avatar', () => {
    const { container } = renderWithTheme(<ChatMessage message={{ id: 'u1', role: 'user', content: 'Hi' }} />)

    const row = screen.getByRole('article', { name: 'Your message' })
    expect(row).toHaveStyle({ flexDirection: 'row-reverse' })
    expect(container.querySelectorAll('svg')).toHaveLength(1)
  })

  it('aligns an assistant message to the left', () => {
    renderWithTheme(<ChatMessage message={assistantMessage('Answer')} />)

    expect(screen.getByRole('article', { name: 'Assistant message' })).toHaveStyle({ flexDirection: 'row' })
  })

  it('shows a system message like an assistant message', () => {
    renderWithTheme(<ChatMessage message={{ id: 's1', role: 'system', content: 'Notice' }} />)

    expect(screen.getByRole('article', { name: 'Assistant message' })).toHaveStyle({ flexDirection: 'row' })
  })
})

describe('ChatMessage bubbles', () => {
  it('gives the user bubble a primary background with contrasting text', () => {
    renderWithTheme(<ChatMessage message={{ id: 'u1', role: 'user', content: 'Hi' }} />)

    expect(bubbleOf('Hi')).toHaveStyle({
      backgroundColor: rgb(appPalette.light.primary),
      color: rgb(appPalette.light.onPrimary),
    })
  })

  it('keeps the user bubble readable in dark mode', () => {
    renderWithTheme(<ChatMessage message={{ id: 'u1', role: 'user', content: 'Hi' }} />, 'dark')

    expect(bubbleOf('Hi')).toHaveStyle({
      backgroundColor: rgb(appPalette.dark.primary),
      color: rgb(appPalette.dark.onPrimary),
    })
  })

  it('gives the assistant bubble a bordered surface with the normal text color', () => {
    renderWithTheme(<ChatMessage message={assistantMessage('Answer')} />)

    const bubble = bubbleOf('Answer')
    expect(bubble).toHaveStyle({ backgroundColor: rgb(appPalette.light.background), color: rgb(appPalette.light.text) })
    expect(bubble).toHaveStyle({ borderStyle: 'solid', borderWidth: '1px' })
  })

  it('limits the column to 78% from the medium breakpoint and uses the full width below it', () => {
    renderWithTheme(<ChatMessage message={assistantMessage('Answer')} />)

    const css = emittedCss()
    expect(css).toContain('max-width:100%')
    expect(css).toContain('max-width:78%')
  })
})

describe('ChatMessage text', () => {
  it('keeps line breaks in the same bubble', () => {
    renderWithTheme(<ChatMessage message={assistantMessage('First line\nSecond line')} />)

    const text = screen.getByText(/First line/)
    expect(text.textContent).toBe('First line\nSecond line')
    expect(text).toHaveStyle({ whiteSpace: 'pre-wrap' })
  })

  it('shows HTML literally and renders nothing from it', () => {
    const html = '<b>Hello</b> <img src=x onerror=alert(1)>'
    const { container } = renderWithTheme(<ChatMessage message={assistantMessage(html)} />)

    expect(screen.getByText(html)).toBeInTheDocument()
    expect(container.querySelector('img')).toBeNull()
    expect(container.querySelector('b')).toBeNull()
  })

  it('does not turn a link into an anchor', () => {
    const { container } = renderWithTheme(<ChatMessage message={assistantMessage('See https://example.com now')} />)

    expect(container.querySelector('a')).toBeNull()
  })
})

describe('ChatMessage decision card', () => {
  it('shows the text bubble first and the decision card below it', () => {
    renderWithTheme(<ChatMessage message={withDecision} />)

    const bubble = bubbleOf(withDecision.content)
    const card = screen.getByRole('region', { name: 'Your trip update' })
    expect(bubble.compareDocumentPosition(card) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  })

  it('shows only the bubble when there is no decision', () => {
    renderWithTheme(<ChatMessage message={assistantMessage('Just text')} />)

    expect(screen.queryByRole('region')).not.toBeInTheDocument()
  })

  it('never shows a card on a user message', () => {
    renderWithTheme(<ChatMessage message={{ ...withDecision, role: 'user' }} />)

    expect(screen.queryByRole('region')).not.toBeInTheDocument()
  })
})
