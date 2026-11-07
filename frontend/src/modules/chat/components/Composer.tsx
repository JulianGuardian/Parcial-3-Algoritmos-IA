import SendIcon from '@mui/icons-material/Send'
import { Box, Chip, IconButton, Paper, TextField, Tooltip, Typography } from '@mui/material'
import { useRef, useState } from 'react'
import type { KeyboardEvent } from 'react'

import { COUNTER_FROM_LENGTH, MAX_MESSAGE_LENGTH, SUGGESTED_QUESTIONS } from './composerConfig'

interface ComposerProps {
  disabled?: boolean
  onSubmit: (message: string) => void | Promise<void>
}

export function Composer({ disabled = false, onSubmit }: Readonly<ComposerProps>) {
  const [message, setMessage] = useState('')
  const [isSending, setIsSending] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement | null>(null)

  const isBusy = disabled || isSending
  const canSend = !isBusy && message.trim().length > 0
  const showCounter = message.length >= COUNTER_FROM_LENGTH

  async function handleSubmit() {
    if (!canSend) {
      return
    }

    setIsSending(true)
    try {
      await onSubmit(message.trim())
      setMessage('')
    } catch {
      // The parent reports the failure; keep the text so the user can send it again.
    } finally {
      setIsSending(false)
    }
  }

  function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    // keyCode 229 is how some browsers report Enter that only confirms an input-method composition.
    const isComposing = event.nativeEvent.isComposing || event.nativeEvent.keyCode === 229

    if (event.key === 'Enter' && !event.shiftKey && !isComposing) {
      event.preventDefault()
      void handleSubmit()
    }
  }

  function handleSuggestion(question: string) {
    if (isBusy) {
      return
    }
    // A suggestion only fills the input: the passenger reviews it and sends it.
    setMessage(question)
    textareaRef.current?.focus()
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
      <Box role="group" aria-label="Suggested questions" sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
        {SUGGESTED_QUESTIONS.map((question) => (
          <Chip
            key={question}
            label={question}
            variant="outlined"
            color="primary"
            disabled={isBusy}
            onClick={() => handleSuggestion(question)}
          />
        ))}
      </Box>

      <Paper
        sx={{
          display: 'flex',
          alignItems: 'flex-end',
          gap: 1.5,
          p: 1.5,
          bgcolor: 'background.default',
          borderColor: 'divider',
        }}
      >
        <TextField
          fullWidth
          multiline
          maxRows={6}
          placeholder="Ask about your flight change..."
          value={message}
          disabled={disabled}
          // slice also covers programmatic changes that skip the maxLength attribute
          onChange={(event) => setMessage(event.target.value.slice(0, MAX_MESSAGE_LENGTH))}
          onKeyDown={handleKeyDown}
          inputRef={textareaRef}
          variant="standard"
          slotProps={{
            input: { disableUnderline: true, sx: { fontSize: '0.98rem', py: 0.5 } },
            htmlInput: { 'aria-label': 'Your question', maxLength: MAX_MESSAGE_LENGTH },
          }}
        />
        <Tooltip title="Send message">
          <span>
            <IconButton
              aria-label="Send message"
              onClick={() => void handleSubmit()}
              disabled={!canSend}
              sx={{
                bgcolor: 'primary.main',
                color: 'primary.contrastText',
                borderRadius: 2,
                p: 1.5,
                '&:hover': { bgcolor: 'primary.dark' },
                '&.Mui-disabled': { bgcolor: 'action.disabledBackground', color: 'action.disabled' },
              }}
            >
              <SendIcon fontSize="small" />
            </IconButton>
          </span>
        </Tooltip>
      </Paper>

      {showCounter ? (
        <Typography variant="caption" color="text.secondary" sx={{ alignSelf: 'flex-end' }}>
          {message.length}/{MAX_MESSAGE_LENGTH}
        </Typography>
      ) : null}
    </Box>
  )
}
