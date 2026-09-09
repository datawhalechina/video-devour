/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        primary: {
          50: "#f1f5ef",
          100: "#e5eddf",
          200: "#cdddc6",
          300: "#acc6a3",
          400: "#7eaa78",
          500: "#527e5c",
          600: "#315e4f",
          700: "#284e41",
          800: "#234237",
          900: "#20382f",
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
        "gradient-brand": "linear-gradient(120deg, #315e4f 0%, #527e5c 100%)",
        "gradient-brand-reverse":
          "linear-gradient(300deg, #66a6ff 0%, #89f7fe 100%)",
        "gradient-brand-horizontal":
          "linear-gradient(90deg, #89f7fe 0%, #77ceff 50%, #66a6ff 100%)",
      },
    },
  },
  plugins: [require("@tailwindcss/typography")],
};
