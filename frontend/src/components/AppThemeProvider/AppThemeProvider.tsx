import { CssBaseline, ThemeProvider } from '@mui/material'
import { useMemo, useSyncExternalStore } from 'react'
import type { ReactNode } from 'react'

import { createAppTheme } from '../../utils/theme'
import type { AppThemeMode } from '../../utils/theme'

const DARK_QUERY = '(prefers-color-scheme: dark)'

function canMatchMedia() {
  return typeof window !== 'undefined' && typeof window.matchMedia === 'function'
}

function subscribe(onChange: () => void) {
  if (!canMatchMedia()) {
    return () => {}
  }

  const query = window.matchMedia(DARK_QUERY)
  query.addEventListener('change', onChange)
  return () => query.removeEventListener('change', onChange)
}

function getSnapshot(): AppThemeMode {
  return canMatchMedia() && window.matchMedia(DARK_QUERY).matches ? 'dark' : 'light'
}

function getServerSnapshot(): AppThemeMode {
  return 'light'
}

interface AppThemeProviderProps {
  children: ReactNode
}

export function AppThemeProvider({ children }: AppThemeProviderProps) {
  const mode = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot)
  const theme = useMemo(() => createAppTheme(mode), [mode])

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      {children}
    </ThemeProvider>
  )
}
