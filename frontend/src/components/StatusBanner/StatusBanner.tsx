import { Alert } from '@mui/material'

interface StatusBannerProps {
  tone?: 'info' | 'error'
  message: string
}

export function StatusBanner({ tone = 'info', message }: StatusBannerProps) {
  const isError = tone === 'error'

  return (
    <Alert
      severity={tone}
      variant="outlined"
      sx={{
        fontWeight: 600,
        bgcolor: isError ? 'rgba(211, 47, 47, 0.06)' : 'background.paper',
        borderColor: isError ? 'rgba(211, 47, 47, 0.24)' : 'divider',
        color: isError ? 'error.main' : 'text.primary',
        '& .MuiAlert-icon': { color: 'inherit' },
      }}
    >
      {message}
    </Alert>
  )
}
