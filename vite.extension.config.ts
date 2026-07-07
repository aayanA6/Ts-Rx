import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { rmSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const __dirname = dirname(fileURLToPath(import.meta.url))

export default defineConfig({
  plugins: [
    react(),
    {
      // Clears only the previous build's hashed bundle files. Vite's default
      // emptyOutDir would delete manifest.json/content.js/vite.svg, which
      // live alongside the build output in extension/ but aren't Vite inputs.
      name: 'clean-stale-extension-assets',
      buildStart() {
        rmSync(resolve(__dirname, 'extension/assets'), { recursive: true, force: true })
      },
    },
  ],
  base: './',
  build: {
    outDir: 'extension',
    emptyOutDir: false,
    assetsDir: 'assets',
  },
})
