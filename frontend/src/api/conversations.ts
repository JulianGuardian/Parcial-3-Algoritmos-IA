import type { AgentResponse, ApiErrorBody, StartConversationResponse } from './types'

const BASE = '/api/v1/conversations'

/** An HTTP error from the API, with the backend's error code when it sent one. */
export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly requestId: string | null

  constructor(status: number, code: string, detail: string, requestId: string | null = null) {
    super(detail)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.requestId = requestId
  }
}

export interface SendMessageInput {
  message: string
  confirmOptionId?: string | null
}

/** Pinned evaluation time for the demo data (the statement's options expire at 2026-09-15T11:04:35Z). */
export function demoNow(): string | null {
  const value = import.meta.env.VITE_DEMO_NOW
  return typeof value === 'string' && value.trim() ? value.trim() : null
}

async function post<T>(url: string, body: unknown): Promise<T> {
  let response: Response
  try {
    response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(body),
    })
  } catch {
    throw new ApiError(0, 'NETWORK_ERROR', 'The assistant could not be reached. Check your connection and try again.')
  }

  if (response.ok) {
    return (await response.json()) as T
  }

  let parsed: Partial<ApiErrorBody> = {}
  try {
    parsed = (await response.json()) as Partial<ApiErrorBody>
  } catch {
    // Non-JSON error body (for example a proxy error page): fall back to the status alone.
  }
  throw new ApiError(
    response.status,
    parsed.error ?? `HTTP_${response.status}`,
    parsed.detail ?? 'Something went wrong. Please try again.',
    parsed.request_id ?? response.headers.get('X-Request-ID'),
  )
}

export function startConversation(bookingId: string): Promise<StartConversationResponse> {
  return post<StartConversationResponse>(BASE, { booking_id: bookingId })
}

export function sendMessage(conversationId: string, input: SendMessageInput): Promise<AgentResponse> {
  const now = demoNow()
  return post<AgentResponse>(`${BASE}/${encodeURIComponent(conversationId)}/messages`, {
    message: input.message,
    ...(input.confirmOptionId ? { confirm_option_id: input.confirmOptionId } : {}),
    ...(now ? { now } : {}),
  })
}
