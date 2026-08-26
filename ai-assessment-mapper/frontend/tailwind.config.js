/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          orange: "#F97316",
          orangeLight: "#FED7AA",
          orangeSoft: "#FFF1E6",
        },
        ink: "#1A1A1A",
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      boxShadow: {
        card: "0 2px 10px rgba(0,0,0,0.04)",
      },
    },
  },
  plugins: [],
};
