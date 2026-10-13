import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import tailwindcss from "@tailwindcss/vite";
export default defineConfig({plugins:[tailwindcss()],resolve:{alias:{"@":fileURLToPath(new URL("./src",import.meta.url))}},build:{outDir:"../web/build",emptyOutDir:true},server:{proxy:{"/api":"http://127.0.0.1:8000"}}});
