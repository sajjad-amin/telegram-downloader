/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: '#007aff',
        'bg-dark': '#0f1115',
        'card-bg': '#1a1d23',
        border: '#2d323a',
        'text-main': '#e1e4e8',
        'text-dim': '#8b949e',
      }
    },
  },
  plugins: [],
}
