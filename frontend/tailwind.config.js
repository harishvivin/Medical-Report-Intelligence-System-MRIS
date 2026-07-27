/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        dark: {
          bg: '#0F172A',
          card: '#1E293B',
          border: '#334155',
          hover: '#475569'
        },
        medical: {
          emerald: '#10B981',
          teal: '#14B8A6',
          cyan: '#06B6D4',
          blue: '#3B82F6',
          purple: '#8B5CF6'
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        'glass': '0 8px 32px 0 rgba(0, 0, 0, 0.37)',
        'glow-emerald': '0 0 20px -3px rgba(16, 185, 129, 0.4)',
      }
    },
  },
  plugins: [],
}
