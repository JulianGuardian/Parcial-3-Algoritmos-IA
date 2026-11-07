import { Box, Button, TextField, Typography } from '@mui/material'
import { useState } from 'react'
import type { FormEvent } from 'react'

interface BookingFormProps {
  onStart: (bookingId: string) => void | Promise<void>
  disabled?: boolean
}

/** First step of the chat: the booking code that binds the conversation. */
export function BookingForm({ onStart, disabled = false }: Readonly<BookingFormProps>) {
  const [bookingId, setBookingId] = useState('')
  const code = bookingId.trim().toUpperCase()

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (code && !disabled) {
      void onStart(code)
    }
  }

  return (
    <Box component="form" onSubmit={handleSubmit} aria-label="Start with your booking" sx={{ display: 'grid', gap: 1.5 }}>
      <Typography variant="body2" color="text.secondary">
        Enter your booking code to start. For the demo, try ABC123, DEF456 or GHI789.
      </Typography>
      <Box sx={{ display: 'flex', gap: 1.5, alignItems: 'flex-start' }}>
        <TextField
          size="small"
          value={bookingId}
          onChange={(event) => setBookingId(event.target.value.slice(0, 20))}
          disabled={disabled}
          placeholder="ABC123"
          slotProps={{ htmlInput: { 'aria-label': 'Booking code', maxLength: 20, autoCapitalize: 'characters' } }}
        />
        <Button type="submit" variant="contained" disabled={disabled || !code}>
          Start
        </Button>
      </Box>
    </Box>
  )
}
