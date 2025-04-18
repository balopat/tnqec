import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
    const env = loadEnv(mode, process.cwd())
    return {
        plugins: [react()],
        server: {
            host: '0.0.0.0', // Allow connections from any IP
            proxy: {
                '/api': {
                    target: env.VITE_BACKEND_URL || 'http://localhost:5000',
                    changeOrigin: true,
                    rewrite: (path) => path.replace(/^\/api/, '')
                }
            }
        }
    }
}) 