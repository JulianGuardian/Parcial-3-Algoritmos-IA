import type { ServerOptions } from 'vite'

/**
 * File-system events do not cross a Windows bind mount into a container, so Vite never sees edits
 * there. Compose sets VITE_USE_POLLING=true to make Vite poll instead; a local run keeps native watching.
 */
export function watchOptions(env: Record<string, string | undefined>): ServerOptions['watch'] {
  return env.VITE_USE_POLLING === 'true' ? { usePolling: true, interval: 300 } : undefined
}
