import { describe, expect, it } from 'vitest'

import { appPalette, createAppTheme, monoFont } from './theme'
import type { StatusKind } from './theme'

function luminance(hex: string) {
  const channels = [1, 3, 5].map((start) => {
    const value = parseInt(hex.slice(start, start + 2), 16) / 255
    return value <= 0.03928 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4
  })
  return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]
}

function contrast(foreground: string, background: string) {
  const [lighter, darker] = [luminance(foreground), luminance(background)].sort((a, b) => b - a)
  return (lighter + 0.05) / (darker + 0.05)
}

const MODES = ['light', 'dark'] as const
const STATUS_KINDS: StatusKind[] = ['onSchedule', 'delayed', 'cancelled', 'confirming']

describe('createAppTheme', () => {
  it('uses the light palette for light mode', () => {
    const theme = createAppTheme('light')

    expect(theme.palette.mode).toBe('light')
    expect(theme.palette.primary.main).toBe(appPalette.light.primary)
    expect(theme.palette.background.paper).toBe(appPalette.light.background)
    expect(theme.palette.divider).toBe(appPalette.light.divider)
  })

  it('uses the dark palette for dark mode', () => {
    const theme = createAppTheme('dark')

    expect(theme.palette.mode).toBe('dark')
    expect(theme.palette.primary.main).toBe(appPalette.dark.primary)
    expect(theme.palette.background.paper).toBe(appPalette.dark.background)
    expect(theme.palette.divider).toBe(appPalette.dark.divider)
  })

  it.each(MODES)('separates page and container surfaces in %s mode', (mode) => {
    const theme = createAppTheme(mode)

    expect(theme.palette.background.default).not.toBe(theme.palette.background.paper)
  })

  it('gives Paper a 1px border in both modes', () => {
    for (const mode of MODES) {
      const paper = createAppTheme(mode).components?.MuiPaper?.styleOverrides?.root as { border?: string }

      expect(paper.border).toBe(`1px solid ${appPalette[mode].border}`)
    }
  })

  it('removes the Paper shadow in dark mode', () => {
    const paper = createAppTheme('dark').components?.MuiPaper?.styleOverrides?.root as { boxShadow?: string }

    expect(paper.boxShadow).toBe('none')
  })

  it('exposes the warning color used by the delayed status', () => {
    expect(createAppTheme('light').palette.warning.main).toBe(appPalette.light.warning)
    expect(createAppTheme('dark').palette.warning.main).toBe(appPalette.dark.warning)
  })

  it.each(MODES)('keeps text readable on every surface in %s mode', (mode) => {
    const colors = appPalette[mode]

    for (const background of [colors.background, colors.backgroundAlt, colors.surface]) {
      expect(contrast(colors.text, background)).toBeGreaterThanOrEqual(4.5)
      expect(contrast(colors.textMuted, background)).toBeGreaterThanOrEqual(4.5)
    }
  })

  it.each(MODES)('keeps status chips readable in %s mode', (mode) => {
    for (const kind of STATUS_KINDS) {
      const { foreground, background } = appPalette[mode].status[kind]

      expect(contrast(foreground, background), `${mode} ${kind}`).toBeGreaterThanOrEqual(4.5)
    }
  })

  it.each(MODES)('keeps text readable on the user bubble in %s mode', (mode) => {
    const colors = appPalette[mode]

    expect(createAppTheme(mode).palette.primary.contrastText).toBe(colors.onPrimary)
    expect(contrast(colors.onPrimary, colors.primary)).toBeGreaterThanOrEqual(4.5)
  })

  it('uses Inter for body text, Manrope for headings and a monospace stack for references', () => {
    const theme = createAppTheme('light')

    expect(theme.typography.fontFamily).toMatch(/^Inter Variable,/)
    expect(theme.typography.h1.fontFamily).toMatch(/^Manrope Variable,/)
    expect(monoFont).toMatch(/monospace$/)
    const baseline = theme.components?.MuiCssBaseline?.styleOverrides as Record<string, Record<string, string>>
    expect(baseline['code, pre, kbd, samp'].fontFamily).toBe(monoFont)
  })
})
