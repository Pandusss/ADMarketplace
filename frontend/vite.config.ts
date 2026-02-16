import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

export default defineConfig({
  // Read a single shared `.env` from the repo root (one .env for backend + frontend).
  // Note: Only variables prefixed with `VITE_` are exposed to the browser by Vite.
  envDir: '../',
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    // Cloudflare Tunnel / Telegram proxying can change the Host header.
    // Vite blocks unknown hosts by default as protection against DNS rebinding.
    // Prefer allowlisting the exact tunnel host (or `.trycloudflare.com`), and only use `true` for temporary local dev.
    allowedHosts: ['.trycloudflare.com'],
    // Dev convenience: proxy API calls to backend to avoid HTTPS->HTTP mixed content
    // when frontend is opened via Cloudflare Tunnel / Telegram WebView.
    proxy: {
      '/api': {
        // Keep same mental model as typical Flask dev: API on 5002.
        // Run: uvicorn app.main:app --port 5002
        target: 'http://127.0.0.1:5002',
        changeOrigin: true,
        secure: false,
        ws: true,
      },
    },
  },
});

