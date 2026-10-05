import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  plugins: [react(), tailwindcss()],
  build: {
    rollupOptions: {
      output: { manualChunks: { charts: ['recharts'] } },
    },
  },
  server: {
    proxy: { '/api': 'http://localhost:8080', '/ws': { target: 'ws://localhost:8080', ws: true } },
  },
  test: { environment: 'jsdom', setupFiles: ['./src/testSetup.ts'] },
});
