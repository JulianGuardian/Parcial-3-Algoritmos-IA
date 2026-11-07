import { Avatar, Box, Paper, Typography } from '@mui/material'

import { BotAvatarIcon } from '../../../icon/BotAvatarIcon'
import { UserAvatarIcon } from '../../../icon/UserAvatarIcon'
import type { Message } from '../types'
import { DecisionCard } from './DecisionCard'

interface ChatMessageProps {
  message: Message
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isAssistantLike = message.role !== 'user'
  const decision = isAssistantLike ? message.decision : null

  return (
    <Box
      role="article"
      aria-label={isAssistantLike ? 'Assistant message' : 'Your message'}
      sx={{
        display: 'flex',
        alignItems: 'flex-start',
        gap: 2,
        flexDirection: isAssistantLike ? 'row' : 'row-reverse',
      }}
    >
      <Avatar
        sx={{
          width: 40,
          height: 40,
          bgcolor: isAssistantLike ? 'primary.light' : 'background.paper',
          color: isAssistantLike ? 'primary.main' : 'text.secondary',
          border: '1px solid',
          borderColor: 'divider',
        }}
      >
        {isAssistantLike ? <BotAvatarIcon style={{ width: 16 }} /> : <UserAvatarIcon style={{ width: 16 }} />}
      </Avatar>

      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          gap: 1.5,
          alignItems: isAssistantLike ? 'flex-start' : 'flex-end',
          minWidth: 0,
          maxWidth: { xs: '100%', md: '78%' },
        }}
      >
        <Paper
          sx={{
            bgcolor: isAssistantLike ? 'background.paper' : 'primary.main',
            color: isAssistantLike ? 'text.primary' : 'primary.contrastText',
            p: 2.5,
            borderTopLeftRadius: isAssistantLike ? 2 : 8,
            borderTopRightRadius: isAssistantLike ? 8 : 2,
            borderColor: isAssistantLike ? 'divider' : 'primary.main',
          }}
        >
          {/* Text node only: nothing in the message is interpreted as markup. */}
          <Typography variant="body2" sx={{ m: 0, fontSize: '0.95rem', whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>
            {message.content}
          </Typography>
        </Paper>

        {decision ? <DecisionCard decision={decision} /> : null}
      </Box>
    </Box>
  )
}
