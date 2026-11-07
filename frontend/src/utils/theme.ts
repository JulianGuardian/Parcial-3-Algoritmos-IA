import { createTheme } from '@mui/material/styles'

export type AppThemeMode = 'light' | 'dark'

export interface StatusColors {
  foreground: string
  background: string
}

export type StatusKind = 'onSchedule' | 'delayed' | 'cancelled' | 'confirming'

export const appPalette = {
  light: {
    primary: '#1547A1',
    primaryStrong: '#123A84',
    primarySoft: '#E8F0FF',
    // Text color on top of the primary color (user bubble, contained buttons).
    onPrimary: '#FFFFFF',
    background: '#FFFFFF',
    backgroundAlt: '#F8F9FA',
    surface: '#F3F4F5',
    text: '#191C1D',
    textMuted: '#434652',
    success: '#2E7D32',
    warning: '#B45309',
    error: '#D32F2F',
    border: '#D7DEE7',
    divider: '#E6EAEE',
    shadow: '0 8px 24px rgba(21, 71, 161, 0.08)',
    // Text and background of the flight status chips.
    status: {
      onSchedule: { foreground: '#1B5E20', background: '#E6F4EA' },
      delayed: { foreground: '#8A4B00', background: '#FFF3E0' },
      cancelled: { foreground: '#B71C1C', background: '#FDECEA' },
      confirming: { foreground: '#434652', background: '#F3F4F5' },
    } satisfies Record<StatusKind, StatusColors>,
  },
  dark: {
    primary: '#3B82F6',
    primaryStrong: '#60A5FA',
    primarySoft: '#172554',
    onPrimary: '#0F172A',
    background: '#0F172A',
    backgroundAlt: '#111C34',
    surface: '#1E293B',
    text: '#F8FAFC',
    textMuted: '#CBD5E1',
    success: '#4ADE80',
    warning: '#FBBF24',
    error: '#F87171',
    border: '#334155',
    divider: '#263244',
    shadow: 'none',
    status: {
      onSchedule: { foreground: '#86EFAC', background: '#14532D' },
      delayed: { foreground: '#FCD34D', background: '#422006' },
      cancelled: { foreground: '#FCA5A5', background: '#450A0A' },
      confirming: { foreground: '#CBD5E1', background: '#1E293B' },
    } satisfies Record<StatusKind, StatusColors>,
  },
} as const

// The variable-font packages register the families as "Inter Variable" and "Manrope Variable".
const bodyFont = ['Inter Variable', 'Inter', 'Segoe UI', 'system-ui', 'sans-serif'].join(',')
const headingFont = ['Manrope Variable', 'Manrope', 'Inter', 'sans-serif'].join(',')
// References (booking, case, policy) use the system monospace stack: no third font is shipped.
export const monoFont = ['ui-monospace', 'SFMono-Regular', 'Consolas', 'Menlo', 'monospace'].join(',')

const headingStyle = {
  fontFamily: headingFont,
  fontWeight: 800,
  letterSpacing: '-0.02em',
}

export function createAppTheme(mode: AppThemeMode) {
  const colors = appPalette[mode]
  const isDark = mode === 'dark'

  return createTheme({
    palette: {
      mode,
      primary: {
        main: colors.primary,
        dark: colors.primaryStrong,
        light: colors.primarySoft,
        contrastText: colors.onPrimary,
      },
      background: {
        default: colors.backgroundAlt,
        paper: colors.background,
      },
      text: {
        primary: colors.text,
        secondary: colors.textMuted,
      },
      success: { main: colors.success },
      warning: { main: colors.warning },
      error: { main: colors.error },
      divider: colors.divider,
    },
    shape: {
      borderRadius: 8,
    },
    typography: {
      fontFamily: bodyFont,
      h1: headingStyle,
      h2: headingStyle,
      h3: headingStyle,
      h4: headingStyle,
      h5: headingStyle,
      h6: headingStyle,
      subtitle1: { fontWeight: 700 },
      button: { fontWeight: 700, textTransform: 'none' },
      body2: { lineHeight: 1.6 },
    },
    components: {
      MuiCssBaseline: {
        styleOverrides: {
          ':root': {
            colorScheme: mode,
          },
          body: {
            backgroundColor: colors.backgroundAlt,
            color: colors.text,
          },
          '*::selection': {
            backgroundColor: isDark ? 'rgba(59, 130, 246, 0.35)' : 'rgba(21, 71, 161, 0.16)',
          },
          'code, pre, kbd, samp': {
            fontFamily: monoFont,
          },
        },
      },
      MuiPaper: {
        styleOverrides: {
          root: {
            backgroundImage: 'none',
            boxShadow: colors.shadow,
            border: `1px solid ${colors.border}`,
          },
        },
      },
      MuiButton: {
        defaultProps: {
          disableElevation: true,
        },
        styleOverrides: {
          root: {
            minHeight: 44,
            borderRadius: 8,
            paddingInline: 18,
          },
        },
        variants: [
          {
            props: { variant: 'contained', color: 'primary' },
            style: {
              '&:hover': {
                backgroundColor: colors.primaryStrong,
              },
            },
          },
        ],
      },
      MuiChip: {
        styleOverrides: {
          root: {
            borderRadius: 8,
            fontWeight: 700,
          },
        },
      },
      MuiAlert: {
        styleOverrides: {
          root: {
            borderRadius: 8,
          },
        },
      },
      MuiTooltip: {
        styleOverrides: {
          tooltip: {
            borderRadius: 8,
            fontSize: '0.75rem',
          },
        },
      },
    },
  })
}
