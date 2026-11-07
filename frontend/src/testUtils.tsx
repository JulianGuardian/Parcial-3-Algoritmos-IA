import { ThemeProvider } from '@mui/material'
import { render } from '@testing-library/react'
import type { ReactElement } from 'react'

import { createAppTheme } from './utils/theme'
import type { AppThemeMode } from './utils/theme'

export function renderWithTheme(ui: ReactElement, mode: AppThemeMode = 'light') {
  const withTheme = (element: ReactElement) => <ThemeProvider theme={createAppTheme(mode)}>{element}</ThemeProvider>
  const result = render(withTheme(ui))

  return {
    ...result,
    // Keep the same wrapper on rerender so the component is updated, not remounted.
    rerender: (nextUi: ReactElement) => result.rerender(withTheme(nextUi)),
  }
}
