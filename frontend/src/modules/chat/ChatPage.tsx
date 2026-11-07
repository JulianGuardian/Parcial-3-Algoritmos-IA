import { Box, Paper, Typography } from '@mui/material'
import { useEffect, useRef } from 'react'

import { StatusBanner } from '../../components/StatusBanner/StatusBanner'
import { ChatMessage } from './components/ChatMessage'
import { Composer } from './components/Composer'
import { EmptyConversationState } from './components/EmptyConversationState'
import type { Message } from './types'

export interface ChatPageProps {
  messages: Message[]
  isLoading?: boolean
  error?: string | null
  isSubmitting?: boolean
  onSubmit: (message: string) => void | Promise<void>
}

const horizontalPadding = { xs: 2, md: 4 }

export function ChatPage({
  messages,
  isLoading = false,
  error = null,
  isSubmitting = false,
  onSubmit,
}: Readonly<ChatPageProps>) {
  const messagesEndRef = useRef<HTMLDivElement>(null)
  // undefined: nothing displayed yet, so the next display is the first one.
  const previousLastMessageIdRef = useRef<string | null | undefined>(undefined)

  const lastMessageId = messages.length > 0 ? messages[messages.length - 1].id : null
  const hasMessages = messages.length > 0

  useEffect(() => {
    if (isLoading) {
      return
    }

    const previousLastMessageId = previousLastMessageIdRef.current
    if (previousLastMessageId === undefined) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'instant', block: 'end' })
    } else if (previousLastMessageId !== lastMessageId) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
    }

    previousLastMessageIdRef.current = lastMessageId
  }, [isLoading, lastMessageId])

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        px: horizontalPadding,
        py: { xs: 2, md: 3 },
        gap: 2,
        bgcolor: 'background.default',
      }}
    >
      {error ? <StatusBanner tone="error" message={error} /> : null}

      <Paper
        sx={{
          flexGrow: 1,
          minHeight: 0,
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          bgcolor: 'background.paper',
        }}
      >
        <Box
          role="log"
          aria-live="polite"
          aria-label="Conversation"
          sx={{
            flexGrow: 1,
            overflowY: 'auto',
            px: horizontalPadding,
            py: 3,
            display: 'flex',
            flexDirection: 'column',
            gap: 3,
            bgcolor: 'background.default',
          }}
        >
          {isLoading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', flexGrow: 1 }}>
              <Typography variant="body2" sx={{ color: 'text.secondary', fontWeight: 600 }}>
                Loading conversation...
              </Typography>
            </Box>
          ) : (
            <>
              {!hasMessages ? <EmptyConversationState /> : null}
              {messages.map((message) => (
                <ChatMessage key={message.id} message={message} />
              ))}
              {/* '1px', not 1: in sx a bare 1 means 100% and would add a full-height blank block. */}
              <Box ref={messagesEndRef} sx={{ height: '1px', flexShrink: 0 }} />
            </>
          )}
        </Box>

        <Box
          sx={{
            px: horizontalPadding,
            pb: { xs: 2, md: 3 },
            pt: 2,
            borderTop: '1px solid',
            borderColor: 'divider',
            bgcolor: 'background.paper',
          }}
        >
          <Composer disabled={isSubmitting} onSubmit={onSubmit} />
        </Box>
      </Paper>
    </Box>
  )
}
