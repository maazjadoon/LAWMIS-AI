/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        canvas: "#030712",
        surface: "#090d16",
        "surface-elevated": "#111827",
      },
      boxShadow: {
        glow: "0 8px 30px rgb(0,0,0,0.4), 0 0 50px -12px rgba(99,102,241,0.12)",
      }
    },
  },
  plugins: [],
}
