/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: '#00ff41',
        dark: '#0a0e27',
        accent: '#00A5FF',
      },
      animation: {
        spin: 'spin 2s linear infinite',
      },
    },
  },
  plugins: [],
}
