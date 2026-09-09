/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#f4f1ff', 100: '#ebe3ff', 200: '#dcc9ff', 300: '#c9a8ff',
          400: '#b088ff', 500: '#9868ff', 600: '#5741e8', 700: '#4a35c9',
          800: '#3d2ca3', 900: '#2f207d',
        },
      },
    },
  },
  plugins: [],
}
