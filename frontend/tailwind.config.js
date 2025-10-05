/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx}',
    './components/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          100: '#e0e7ff',
          200: '#c7d2fe',
          400: '#818cf8',
          600: '#4f46e5',
          700: '#4338ca',
          800: '#3730a3',
        },
      },
    },
  },
  plugins: [],
};


