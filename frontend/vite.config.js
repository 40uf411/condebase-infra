import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const allowedHosts = ["app.local", "localhost"];

export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 3000,
    allowedHosts,
  },
  preview: {
    allowedHosts,
  },
});
