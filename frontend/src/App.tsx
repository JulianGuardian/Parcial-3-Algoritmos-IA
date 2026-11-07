import { useState } from 'react'

import { ChatPage } from './modules/chat'
import { sampleMessages } from './modules/chat/fixtures'
import type { Message } from './modules/chat/types'

function App() {
  // The example conversation is temporary: it is removed, with this wiring, when the chat is connected to the API.
  const [messages, setMessages] = useState<Message[]>(sampleMessages)

  function handleSubmit(text: string) {
    setMessages((current) => [...current, { id: crypto.randomUUID(), role: 'user', content: text }])
  }

  return <ChatPage messages={messages} onSubmit={handleSubmit} />
}

export default App
