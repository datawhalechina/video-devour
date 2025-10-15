/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        primary: {
          50: "#f0f9ff",
          100: "#e0f2fe",
          200: "#bae6fd",
          300: "#7dd3fc",
          400: "#38bdf8",
          500: "#0ea5e9",
          600: "#0284c7",
          700: "#0369a1",
          800: "#075985",
          900: "#0c4a6e",
        },
        // 主题渐变色系统
        brand: {
          start: "#89f7fe", // 渐变起始色（浅青色）
          middle: "#77ceff", // 渐变中间色
          end: "#66a6ff", // 渐变结束色（蓝色）
          light: "#e3f8ff", // 浅色背景
          dark: "#4d8fd9", // 深色变体
        },
      },
      backgroundImage: {
        // 主题渐变
        "gradient-brand": "linear-gradient(120deg, #89f7fe 0%, #66a6ff 100%)",
        "gradient-brand-reverse":
          "linear-gradient(300deg, #66a6ff 0%, #89f7fe 100%)",
        "gradient-brand-horizontal":
          "linear-gradient(90deg, #89f7fe 0%, #77ceff 50%, #66a6ff 100%)",
      },
    },
  },
  plugins: [require("@tailwindcss/typography")],
};
