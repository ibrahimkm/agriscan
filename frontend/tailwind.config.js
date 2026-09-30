/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        agri: {
          green: {
            50: '#F0F7F4',
            100: '#D8ECE2',
            200: '#B2D8C6',
            500: '#2D6A4F',
            600: '#1E4D38',
            700: '#1B4332',
            800: '#14382B',
            900: '#0D271E',
          },
          cream: {
            50: '#FCFBF9',
            100: '#F8F6F0',
            200: '#F0ECE1',
            300: '#E4DDD0',
            400: '#D2C7B4',
          },
          sand: {
            100: '#F5EBE1',
            200: '#EBD8C3',
            300: '#DDBFA1',
            400: '#D4A373',
            500: '#C68B59',
            600: '#A46B3C',
          },
          status: {
            healthy: '#22C55E',
            healthyBg: '#EDF7EE',
            healthyText: '#15803D',
            risk: '#EAB308',
            riskBg: '#FEF9C3',
            riskText: '#A16207',
            diseased: '#EF4444',
            diseasedBg: '#FEE2E2',
            diseasedText: '#B91C1C',
          }
        }
      },
      fontFamily: {
        sans: ['Plus Jakarta Sans', 'Inter', 'system-ui', 'sans-serif'],
        serif: ['Lora', 'Georgia', 'serif'],
      },
      borderRadius: {
        '2xl': '1rem',
        '3xl': '1.5rem',
        '4xl': '2rem',
      },
      boxShadow: {
        'soft': '0 2px 12px -2px rgba(27, 67, 50, 0.06), 0 1px 4px -1px rgba(27, 67, 50, 0.04)',
        'elevated': '0 10px 25px -4px rgba(27, 67, 50, 0.12), 0 4px 8px -2px rgba(27, 67, 50, 0.06)',
      }
    },
  },
  plugins: [],
}
