/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'dark-primary': '#0f172a',
        'dark-secondary': '#1e293b',
        'dark-tertiary': '#334155',
        'accent-blue': '#3b82f6',
        'accent-green': '#10b981',
        'accent-orange': '#f97316',
      }
    },
  },
  plugins: [],
}
