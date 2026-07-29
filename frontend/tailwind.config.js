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
          sky: '#0EA5E9',
          blue: '#2563EB',
          indigo: '#6366F1',
          cyan: '#06B6D4',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        'glass': '0 8px 32px 0 rgba(0, 0, 0, 0.37)',
        'glow-sky': '0 0 20px -3px rgba(14, 165, 233, 0.45)',
        'glow-blue': '0 0 20px -3px rgba(37, 99, 235, 0.45)',
      }
    },
  },
  plugins: [],
}
