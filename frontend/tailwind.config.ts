import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        "on-error": "#ffffff",
        "on-primary-fixed-variant": "#215100",
        "tertiary-fixed": "#ffdcc4",
        "on-tertiary-fixed": "#2f1400",
        "secondary-fixed-dim": "#b7c9d2",
        primary: "#2e6c00",
        "on-primary": "#ffffff",
        "outline-variant": "#c0cab5",
        "on-tertiary": "#ffffff",
        "surface-bright": "#f3fbff",
        "surface-tint": "#2e6c00",
        "surface-container": "#def1fa",
        "on-primary-fixed": "#092100",
        "surface-container-lowest": "#ffffff",
        error: "#ba1a1a",
        "inverse-surface": "#22333a",
        "surface-container-highest": "#d3e5ee",
        "tertiary-fixed-dim": "#ffb781",
        "secondary-fixed": "#d3e5ee",
        "on-primary-container": "#1b4600",
        "on-secondary-container": "#54656d",
        "on-surface": "#0c1e24",
        "primary-container": "#6cba3d",
        "on-tertiary-container": "#602f00",
        tertiary: "#934b00",
        surface: "#f3fbff",
        "on-secondary-fixed-variant": "#384950",
        "surface-container-low": "#e5f6ff",
        background: "#f3fbff",
        outline: "#717a68",
        "on-background": "#0c1e24",
        "on-surface-variant": "#414939",
        "on-error-container": "#93000a",
        "inverse-on-surface": "#e1f4fd",
        "secondary-container": "#d0e3eb",
        "primary-fixed-dim": "#8adb5a",
        secondary: "#506168",
        "error-container": "#ffdad6",
        "surface-dim": "#cadde6",
        "on-secondary-fixed": "#0c1e24",
        "tertiary-container": "#f58d31",
        "surface-container-high": "#d9ebf4",
        "on-secondary": "#ffffff",
        "primary-fixed": "#a5f873",
        "inverse-primary": "#8adb5a",
        "on-tertiary-fixed-variant": "#703800",
        "surface-variant": "#d3e5ee"
      },
      borderRadius: {
        DEFAULT: "0.25rem",
        lg: "0.5rem",
        xl: "1.5rem",
        full: "9999px"
      },
      boxShadow: {
        soft: "0 12px 32px rgba(12,30,36,0.06)"
      },
      fontFamily: {
        headline: ["Lexend", "sans-serif"],
        body: ["Lexend", "sans-serif"],
        label: ["Lexend", "sans-serif"]
      }
    }
  },
  plugins: []
};

export default config;
