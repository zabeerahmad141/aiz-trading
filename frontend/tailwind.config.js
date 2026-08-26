/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: {
          primary: '#060b14',
          secondary: '#0d1526',
          card: 'rgba(13, 21, 38, 0.85)',
        },
        brand: {
          blue: '#00d4ff',
          gold: '#ffc400',
          green: '#00e676',
          red: '#ff3d71',
        },
        text: {
          primary: '#e8f0fe',
          secondary: '#7a8fa6',
          muted: '#3d5166',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      animation: {
        'pulse-glow': 'pulse-glow 2s ease-in-out infinite',
        'ticker': 'ticker 40s linear infinite',
        'fade-in': 'fade-in 0.3s ease',
        'slide-up': 'slide-up 0.3s ease',
        'count-up': 'count-up 0.8s ease',
      },
      keyframes: {
        'pulse-glow': {
          '0%, 100%': { boxShadow: '0 0 5px rgba(0,212,255,0.3)' },
          '50%': { boxShadow: '0 0 20px rgba(0,212,255,0.6)' },
        },
        'fade-in': {
          from: { opacity: '0', transform: 'translateY(4px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        'slide-up': {
          from: { opacity: '0', transform: 'translateY(16px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
      },
      backdropBlur: { xl: '20px' },
    },
  },
  plugins: [],
};
