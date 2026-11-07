import { useState } from 'react'

import { ApiError, sendMessage, startConversation } from './api/conversations'
import { toDecisionView } from './api/mapper'
import { ChatPage } from './modules/chat'
import { BookingForm } from './modules/chat/components/BookingForm'
import { formatDate } from './utils/time'
import type { Message, RecommendedOption } from './modules/chat/types'

interface Conversation {
  id: string
  bookingId: string
}

function errorText(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.code === 'BOOKING_NOT_FOUND') {
      return 'We could not find that booking. Check the code and try again.'
    }
    if (error.status === 503 || error.status === 0) {
      return error.message
    }
  }
  return 'Something went wrong. Please try again.'
}

function App() {
  const [conversation, setConversation] = useState<Conversation | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleStart(bookingId: string) {
    setIsSubmitting(true)
    setError(null)
    try {
      const started = await startConversation(bookingId)
      setConversation({ id: started.conversation_id, bookingId: started.booking_id })
      setMessages([])
    } catch (caught) {
      setError(errorText(caught))
    } finally {
      setIsSubmitting(false)
    }
  }

  async function send(text: string, confirmOptionId?: string) {
    if (!conversation) {
      return
    }
    setIsSubmitting(true)
    setError(null)
    setMessages((current) => [...current, { id: crypto.randomUUID(), role: 'user', content: text }])
    try {
      const response = await sendMessage(conversation.id, { message: text, confirmOptionId })
      setMessages((current) => [
        ...current,
        { id: crypto.randomUUID(), role: 'assistant', content: response.reply, decision: toDecisionView(response) },
      ])
    } catch (caught) {
      // The passenger's message was not answered: remove it so it can be sent again.
      setMessages((current) => current.slice(0, -1))
      if (caught instanceof ApiError && caught.code === 'CONVERSATION_NOT_FOUND') {
        setConversation(null)
        setMessages([])
        setError('Your conversation expired. Enter your booking code to start again.')
        return
      }
      setError(errorText(caught))
      // Re-throw so the composer keeps the typed text.
      throw caught
    } finally {
      setIsSubmitting(false)
    }
  }

  function handleConfirm(option: RecommendedOption) {
    if (!option.option_id) {
      return
    }
    const when = [formatDate(option.date), option.departure].filter(Boolean).join(' at ')
    const text = `I confirm flight ${option.flight_number ?? option.option_id}${when ? ` on ${when}` : ''}.`
    void send(text, option.option_id).catch(() => undefined)
  }

  return (
    <ChatPage
      messages={messages}
      error={error}
      isSubmitting={isSubmitting}
      onSubmit={(text) => send(text)}
      onConfirm={handleConfirm}
      footer={conversation ? undefined : <BookingForm onStart={handleStart} disabled={isSubmitting} />}
    />
  )
}

export default App
