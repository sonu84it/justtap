import express from "express";
import path from "path";
import { fileURLToPath } from "url";

const app = express();
const port = Number(process.env.PORT || 8080);
const currentFile = fileURLToPath(import.meta.url);
const currentDir = path.dirname(currentFile);
const distDir = path.join(currentDir, "dist");

app.use(express.static(distDir));

app.get("*", (request, response) => {
  // Only app routes should fall back to index.html. Missing asset URLs must
  // return 404 so browsers do not try to execute HTML as JavaScript.
  if (path.extname(request.path)) {
    response.status(404).end();
    return;
  }

  response.sendFile(path.join(distDir, "index.html"));
});

app.listen(port, () => {
  console.log(`Frontend server listening on port ${port}`);
});
