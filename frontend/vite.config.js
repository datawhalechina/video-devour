import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      // 报告中的关键帧图片由后端静态目录提供，必须一并代理
      "/static": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
