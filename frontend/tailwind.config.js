/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx,js,jsx}'],
  theme: {
    extend: {
      colors: {
        brand: { 400: '#6EE7F9' }
      },
      boxShadow: {
        'neo-sm': '8px 8px 16px var(--shadow-dark), -8px -8px 16px var(--shadow-light)',
        'neo': '16px 16px 32px var(--shadow-dark), -16px -16px 32px var(--shadow-light)',
        'neo-inset': 'inset 8px 8px 16px var(--shadow-dark), inset -8px -8px 16px var(--shadow-light)'
      }
    },
  },
  plugins: [],
}