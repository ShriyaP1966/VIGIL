/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: {
          main: '#0B1020',
          sidebar: '#0F172A',
          card: '#111827',
          elevated: '#1E293B',
        },
        border: {
          subtle: '#263248',
          focus: '#38BDF8',
        },
        accent: {
          primary: '#38BDF8',
          secondary: '#2DD4BF',
        },
        risk: {
          low: '#22C55E',
          elevated: '#EAB308',
          high: '#F59E0B',
          critical: '#EF4444',
        },
        text: {
          primary: '#F8FAFC',
          secondary: '#94A3B8',
          muted: '#64748B',
        }
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      }
    },
  },
  plugins: [],
}
