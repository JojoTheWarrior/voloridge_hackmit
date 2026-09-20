/// <reference types="vitest/config" />
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // xfwd passes the browser's own host along, which the server needs to write an explorer's content policy.
    proxy: { '/api': { target: process.env.KINGDOM_API_TARGET ?? 'http://127.0.0.1:8030', xfwd: true } },
  },
  test: {
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    globals: true,
  },
})
