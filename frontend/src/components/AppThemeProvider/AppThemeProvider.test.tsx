import { useTheme } from '@mui/material'
import { act, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { appPalette } from '../../utils/theme'
import { AppThemeProvider } from './AppThemeProvider'

function mockSystemScheme(initiallyDark: boolean) {
  let dark = initiallyDark
  const listeners = new Set<() => void>()

  window.matchMedia = vi.fn((query: string) => ({
    get matches() {
      return dark
    },
    media: query,
    addEventListener: (_event: string, listener: () => void) => listeners.add(listener),
    removeEventListener: (_event: string, listener: () => void) => listeners.delete(listener),
  })) as unknown as typeof window.matchMedia

  return {
    change(nextDark: boolean) {
      dark = nextDark
      listeners.forEach((listener) => listener())
    },
  }
}

function ModeProbe() {
  const theme = useTheme()
  return (
    <p>
      {theme.palette.mode}:{theme.palette.primary.main}
    </p>
  )
}

function renderProvider() {
  return render(
    <AppThemeProvider>
      <ModeProbe />
    </AppThemeProvider>,
  )
}

describe('AppThemeProvider', () => {
  afterEach(() => {
    // jsdom has no matchMedia; remove the mock so each test installs its own
    Reflect.deleteProperty(window, 'matchMedia')
  })

  it('uses the dark palette when the system prefers dark at load', () => {
    mockSystemScheme(true)
    renderProvider()

    expect(screen.getByText(`dark:${appPalette.dark.primary}`)).toBeInTheDocument()
  })

  it('uses the light palette when the system prefers light at load', () => {
    mockSystemScheme(false)
    renderProvider()

    expect(screen.getByText(`light:${appPalette.light.primary}`)).toBeInTheDocument()
  })

  it('switches palette when the system preference changes while open', () => {
    const system = mockSystemScheme(false)
    renderProvider()
    expect(screen.getByText(`light:${appPalette.light.primary}`)).toBeInTheDocument()

    act(() => system.change(true))

    expect(screen.getByText(`dark:${appPalette.dark.primary}`)).toBeInTheDocument()
  })

  it('falls back to the light palette when matchMedia is unavailable', () => {
    renderProvider()

    expect(screen.getByText(`light:${appPalette.light.primary}`)).toBeInTheDocument()
  })
})
