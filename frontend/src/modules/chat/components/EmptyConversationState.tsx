import { Box, Typography } from '@mui/material'

import { BotAvatarIcon } from '../../../icon/BotAvatarIcon'

export function EmptyConversationState() {
  return (
    <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
      <Box
        sx={{
          width: 40,
          height: 40,
          borderRadius: '50%',
          bgcolor: 'primary.light',
          color: 'primary.main',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
        }}
      >
        <BotAvatarIcon style={{ width: 18 }} />
      </Box>

      <Box
        sx={{
          bgcolor: 'background.paper',
          color: 'text.primary',
          p: 2.5,
          borderRadius: 3,
          borderTopLeftRadius: 4,
          maxWidth: '75%',
        }}
      >
        <Typography variant="body2" sx={{ fontSize: '0.95rem' }}>
          Hello. I am the <strong>Nubara flight assistant</strong>. Ask me about a change to your flight and I
          will explain what happened and what you can do next.
        </Typography>
      </Box>
    </Box>
  )
}
