import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // host: true 监听 0.0.0.0，同一局域网的其他电脑可直接访问（开发模式）
    host: true,
    port: 3000,
    strictPort: true,
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
