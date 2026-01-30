import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const root = path.join(__dirname, "..");
const src = path.join(root, "public", "qa.html");
const distDir = path.join(root, "dist");
const dst = path.join(distDir, "qa.html");

if (!fs.existsSync(src)) {
    console.error("❌ public/qa.html não encontrado");
    process.exit(1);
}

if (!fs.existsSync(distDir)) {
    fs.mkdirSync(distDir, { recursive: true });
}

fs.copyFileSync(src, dst);

if (!fs.existsSync(dst)) {
    console.error("❌ Falha ao gerar dist/qa.html");
    process.exit(1);
}

console.log("✅ QA Runner publicado em dist/qa.html");
