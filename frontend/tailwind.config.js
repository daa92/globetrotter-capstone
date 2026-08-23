/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        // Grounded in Cameroon's own landscape rather than a generic
        // palette: rainforest canopy green, laterite red-clay road, and
        // savanna gold-hour light. See AnimatedCanopyBackground.jsx for
        // where these come together as the site's signature motif.
        canopy: { 300: "#6FBE93", 500: "#1F7A4D", 700: "#14301F", 900: "#0B1A12" },
        laterite: { 400: "#E07850", 600: "#C1502E" },
        goldhour: { 400: "#F2C765", 500: "#E8B23D" },
        sand: { 50: "#FBF7EC", 100: "#F4EEDD" },
      },
      fontFamily: {
        display: ["Fraunces", "serif"],
        body: ["Manrope", "sans-serif"],
        data: ["\"IBM Plex Mono\"", "monospace"],
      },
    },
  },
  plugins: [],
};
