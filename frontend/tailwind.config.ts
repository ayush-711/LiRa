import type { Config } from "tailwindcss";

// Colors are CSS variables carrying RGB triplets; this helper wires them up so
// Tailwind opacity modifiers (bg-surface/60, ring-brand/30, …) keep working and
// the whole palette can be theme-swapped by redefining the variables.
const v = (name: string) => `rgb(var(--${name}) / <alpha-value>)`;

const config: Config = {
  darkMode: ["selector", '[data-theme="dark"]'],
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: v("bg"),
        surface: v("surface"),
        "surface-2": v("surface-2"),
        border: v("border"),
        muted: v("muted"),
        fg: v("fg"),
        "fg-subtle": v("fg-subtle"),
        brand: {
          DEFAULT: v("accent"),
          fg: v("accent-fg"),
          soft: v("accent-soft"),
        },
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
      },
      borderRadius: {
        xl: "14px",
      },
      boxShadow: {
        soft: "0 1px 2px rgb(0 0 0 / 0.04), 0 1px 3px rgb(0 0 0 / 0.03)",
        pop: "0 12px 40px rgb(0 0 0 / 0.14)",
      },
    },
  },
  plugins: [],
};
export default config;
