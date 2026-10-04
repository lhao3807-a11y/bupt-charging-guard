import { defineConfig, mergeConfig } from 'vitest/config'
import viteConfig from './vite.config'

export default mergeConfig(viteConfig, defineConfig({
  // Vue component tests use a memory renderer; compile SFCs for the client.
  test: { environment: './scripts/vitest-memory-host.mjs' },
}))
