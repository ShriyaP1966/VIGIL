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
          critical: '#F87171',     // 5.3:1 on the lightest panel; also readable as a solid fill with dark text
        },
        text: {
          primary: '#F8FAFC',
          secondary: '#94A3B8',
          muted: '#8796AB',     // 4.9:1 on the lightest panel (WCAG AA); the earlier #64748B measured 3.1-3.7:1
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
