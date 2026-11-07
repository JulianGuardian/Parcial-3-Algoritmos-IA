import { afterEach, describe, expect, it, vi } from 'vitest'

import { ApiError, sendMessage, startConversation } from './conversations'
import { abc123Response } from './sampleResponses'

function jsonResponse(status: number, body: unknown) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

function mockFetch(response: Response | Error) {
  const fetchMock = vi.fn<(url: string, init?: RequestInit) => Promise<Response>>(() =>
    response instanceof Error ? Promise.reject(response) : Promise.resolve(response),
  )
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

function sentBody(fetchMock: ReturnType<typeof mockFetch>) {
  const [, init] = fetchMock.mock.calls[0]
  return JSON.parse(String(init?.body))
}

afterEach(() => {
  vi.unstubAllGlobals()
  vi.unstubAllEnvs()
})

describe('startConversation', () => {
  it('posts the booking id to the same-origin API', async () => {
    const fetchMock = mockFetch(jsonResponse(201, { conversation_id: 'c-1', booking_id: 'ABC123' }))

    const started = await startConversation('ABC123')

    expect(started).toEqual({ conversation_id: 'c-1', booking_id: 'ABC123' })
    expect(fetchMock.mock.calls[0][0]).toBe('/api/v1/conversations')
    expect(sentBody(fetchMock)).toEqual({ booking_id: 'ABC123' })
  })

  it('turns a backend error into an ApiError with its code and request id', async () => {
    mockFetch(jsonResponse(404, { error: 'BOOKING_NOT_FOUND', detail: 'No booking matches this id.', request_id: 'r-9' }))

    const error = await startConversation('ZZZ999').catch((caught: unknown) => caught)

    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({ status: 404, code: 'BOOKING_NOT_FOUND', requestId: 'r-9' })
  })

  it('reports a network failure as NETWORK_ERROR', async () => {
    mockFetch(new TypeError('Failed to fetch'))

    await expect(startConversation('ABC123')).rejects.toMatchObject({ status: 0, code: 'NETWORK_ERROR' })
  })
})

describe('sendMessage', () => {
  it('sends only the message when there is no confirmation or pinned time', async () => {
    const fetchMock = mockFetch(jsonResponse(200, abc123Response))

    const response = await sendMessage('c-1', { message: 'What happened?' })

    expect(fetchMock.mock.calls[0][0]).toBe('/api/v1/conversations/c-1/messages')
    expect(sentBody(fetchMock)).toEqual({ message: 'What happened?' })
    expect(response.next_step).toBe('AGENT_WILL_CONTACT')
  })

  it('adds confirm_option_id and the pinned demo time when present', async () => {
    vi.stubEnv('VITE_DEMO_NOW', '2026-09-15T11:03:00Z')
    const fetchMock = mockFetch(jsonResponse(200, abc123Response))

    await sendMessage('c-1', { message: 'I confirm flight NB2412.', confirmOptionId: 'O1' })

    expect(sentBody(fetchMock)).toEqual({
      message: 'I confirm flight NB2412.',
      confirm_option_id: 'O1',
      now: '2026-09-15T11:03:00Z',
    })
  })

  it('keeps a generic message when the error body is not JSON', async () => {
    mockFetch(new Response('<html>Bad gateway</html>', { status: 502 }))

    await expect(sendMessage('c-1', { message: 'Hi' })).rejects.toMatchObject({
      status: 502,
      code: 'HTTP_502',
      message: 'Something went wrong. Please try again.',
    })
  })
})
