import { describe, expect, it } from 'vitest'

import { watchOptions } from './vite.watch.ts'

describe('watchOptions', () => {
  it('polls every 300 ms when VITE_USE_POLLING is "true"', () => {
    expect(watchOptions({ VITE_USE_POLLING: 'true' })).toEqual({ usePolling: true, interval: 300 })
  })

  it('keeps native file watching when the variable is not set', () => {
    expect(watchOptions({})).toBeUndefined()
  })

  it.each(['false', '', '1', 'TRUE'])('keeps native file watching for "%s"', (value) => {
    expect(watchOptions({ VITE_USE_POLLING: value })).toBeUndefined()
  })
})
