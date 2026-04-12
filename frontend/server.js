import express from "express";
import path from "path";
import { fileURLToPath } from "url";

const app = express();
const port = Number(process.env.PORT || 8080);
const currentFile = fileURLToPath(import.meta.url);
const currentDir = path.dirname(currentFile);
const distDir = path.join(currentDir, "dist");

app.use(express.static(distDir));

app.get("*", (_request, response) => {
  response.sendFile(path.join(distDir, "index.html"));
});

app.listen(port, () => {
  console.log(`Frontend server listening on port ${port}`);
});
