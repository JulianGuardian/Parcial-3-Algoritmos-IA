import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import App from './App'
import { abc123Response, def456PendingResponse, def456Response } from './api/sampleResponses'
import { renderWithTheme } from './testUtils'

type Reply = { status: number; body: unknown }

function json({ status, body }: Reply) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

/** Answers each call with the next reply and records the request bodies. */
function mockApi(...replies: Reply[]) {
  const queue = [...replies]
  const fetchMock = vi.fn<(url: string, init?: RequestInit) => Promise<Response>>(() => {
    const next = queue.shift()
    if (!next) {
      throw new Error('unexpected request')
    }
    return Promise.resolve(json(next))
  })
  vi.stubGlobal('fetch', fetchMock)
  const bodies = () => fetchMock.mock.calls.map(([url, init]) => ({ url, body: JSON.parse(String(init?.body)) }))
  return { fetchMock, bodies }
}

const started = (bookingId: string): Reply => ({ status: 201, body: { conversation_id: 'c-1', booking_id: bookingId } })

async function startWith(user: ReturnType<typeof userEvent.setup>, code: string) {
  await user.type(screen.getByRole('textbox', { name: 'Booking code' }), code)
  await user.click(screen.getByRole('button', { name: 'Start' }))
}

beforeEach(() => {
  Element.prototype.scrollIntoView = vi.fn()
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('App', () => {
  it('starts on the booking step with the messages area and no composer', () => {
    mockApi()
    renderWithTheme(<App />)

    expect(screen.getByRole('log', { name: 'Conversation' })).toBeInTheDocument()
    expect(screen.getByRole('textbox', { name: 'Booking code' })).toBeInTheDocument()
    expect(screen.queryByRole('textbox', { name: 'Your question' })).not.toBeInTheDocument()
  })

  it('starts a conversation for ABC123 and enables the composer', async () => {
    const user = userEvent.setup({ delay: null })
    const api = mockApi(started('ABC123'))
    renderWithTheme(<App />)

    await startWith(user, 'abc123')

    expect(await screen.findByRole('textbox', { name: 'Your question' })).toBeInTheDocument()
    expect(api.bodies()).toEqual([{ url: '/api/v1/conversations', body: { booking_id: 'ABC123' } }])
  })

  it('stays on the booking step when the booking is unknown', async () => {
    const user = userEvent.setup({ delay: null })
    mockApi({ status: 404, body: { error: 'BOOKING_NOT_FOUND', detail: 'No booking matches this id.' } })
    renderWithTheme(<App />)

    await startWith(user, 'ZZZ999')

    expect(await screen.findByText(/We could not find that booking/)).toBeInTheDocument()
    expect(screen.getByRole('textbox', { name: 'Booking code' })).toBeInTheDocument()
  })

  it('shows the agent reply and the trip-update card for ABC123, without a confirm button', async () => {
    const user = userEvent.setup({ delay: null })
    const api = mockApi(started('ABC123'), { status: 200, body: abc123Response })
    renderWithTheme(<App />)
    await startWith(user, 'ABC123')

    await user.type(await screen.findByRole('textbox', { name: 'Your question' }), 'What happened to my flight?{Enter}')

    const card = await screen.findByRole('region', { name: 'Your trip update' })
    expect(screen.getByText(abc123Response.reply)).toBeInTheDocument()
    expect(within(card).getByText('NB2412')).toBeInTheDocument()
    expect(within(card).getByText('POL-DELAY-2026-03')).toBeInTheDocument()
    expect(within(card).queryByRole('button', { name: 'Confirm this option' })).not.toBeInTheDocument()
    expect(api.bodies()[1]).toEqual({ url: '/api/v1/conversations/c-1/messages', body: { message: 'What happened to my flight?' } })
  })

  it('confirms the DEF456 option with confirm_option_id and shows the pending request', async () => {
    const user = userEvent.setup({ delay: null })
    const api = mockApi(started('DEF456'), { status: 200, body: def456Response }, { status: 200, body: def456PendingResponse })
    renderWithTheme(<App />)
    await startWith(user, 'DEF456')
    await user.type(await screen.findByRole('textbox', { name: 'Your question' }), 'What are my options?{Enter}')

    await user.click(await screen.findByRole('button', { name: 'Confirm this option' }))

    await waitFor(() => expect(api.bodies()).toHaveLength(3))
    expect(api.bodies()[2].body).toEqual({ message: 'I confirm flight NB2412 on 16 Sep 2026 at 08:15.', confirm_option_id: 'O1' })
    expect(await screen.findByText(/We have requested this change\. You will receive/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Confirm this option' })).not.toBeInTheDocument()
  })

  it('goes back to the booking step when the conversation expired', async () => {
    const user = userEvent.setup({ delay: null })
    mockApi(started('ABC123'), { status: 404, body: { error: 'CONVERSATION_NOT_FOUND', detail: 'No conversation matches this id.' } })
    renderWithTheme(<App />)
    await startWith(user, 'ABC123')

    await user.type(await screen.findByRole('textbox', { name: 'Your question' }), 'Hello{Enter}')

    expect(await screen.findByText(/Your conversation expired/)).toBeInTheDocument()
    expect(screen.getByRole('textbox', { name: 'Booking code' })).toBeInTheDocument()
  })

  it('keeps the typed text and shows a banner when the agent is unavailable', async () => {
    const user = userEvent.setup({ delay: null })
    mockApi(started('ABC123'), {
      status: 503,
      body: { error: 'UPSTREAM_UNAVAILABLE', detail: 'A required data source is unavailable. Try again later.' },
    })
    renderWithTheme(<App />)
    await startWith(user, 'ABC123')
    const input = await screen.findByRole('textbox', { name: 'Your question' })

    await user.type(input, 'What happened?{Enter}')

    expect(await screen.findByText('A required data source is unavailable. Try again later.')).toBeInTheDocument()
    expect(input).toHaveValue('What happened?')
    expect(screen.queryByRole('article', { name: 'Your message' })).not.toBeInTheDocument()
  })
})
