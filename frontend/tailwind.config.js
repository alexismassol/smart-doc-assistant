/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#0a0a0a',
        surface: '#111111',
        elevated: '#1a1a1a',
        border: '#1f1f1f',
        'border-bright': '#2a2a2a',
        accent: '#8b5cf6',
        'accent-hover': '#7c3aed',
        'accent-dim': 'rgba(139,92,246,0.15)',
        text: '#f5f5f5',
        'text-secondary': '#a3a3a3',
        'text-dim': '#525252',
        success: '#10b981',
        error: '#ef4444',
        warning: '#f59e0b',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      animation: {
        'fade-in': 'fadeIn 0.2s ease-out',
        'slide-up': 'slideUp 0.25s ease-out',
        'pulse-slow': 'pulse 2s cubic-bezier(0.4,0,0.6,1) infinite',
        'typing': 'typing 1.2s steps(3) infinite',
      },
      keyframes: {
        fadeIn: { from: { opacity: '0' }, to: { opacity: '1' } },
        slideUp: { from: { opacity: '0', transform: 'translateY(8px)' }, to: { opacity: '1', transform: 'translateY(0)' } },
        typing: {
          '0%,100%': { content: '.' },
          '33%': { content: '..' },
          '66%': { content: '...' },
        },
      },
      boxShadow: {
        'glow-sm': '0 0 12px rgba(139,92,246,0.2)',
        'glow': '0 0 24px rgba(139,92,246,0.25)',
        'glow-lg': '0 0 40px rgba(139,92,246,0.3)',
      },
    },
  },
  plugins: [],
}
