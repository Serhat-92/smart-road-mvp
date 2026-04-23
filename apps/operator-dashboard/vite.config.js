import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { createReadStream, existsSync } from "node:fs";
import { extname, isAbsolute, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const dashboardRoot = fileURLToPath(new URL(".", import.meta.url));
const repoRoot = resolve(dashboardRoot, "..", "..");
const evidenceRoot = resolve(repoRoot, "datasets", "evidence");

function contentTypeFor(filePath) {
  const extension = extname(filePath).toLowerCase();
  if (extension === ".png") {
    return "image/png";
  }
  if (extension === ".webp") {
    return "image/webp";
  }
  return "image/jpeg";
}

function localEvidencePlugin() {
  function handleEvidenceRequest(request, response, next) {
    const requestUrl = new URL(request.url, "http://localhost");
    if (requestUrl.pathname !== "/local-evidence") {
      next();
      return;
    }

    const rawPath = requestUrl.searchParams.get("path");
    if (!rawPath) {
      response.statusCode = 400;
      response.end("Missing evidence path");
      return;
    }

    const requestedPath = isAbsolute(rawPath)
      ? resolve(rawPath)
      : resolve(repoRoot, rawPath);
    const relativeEvidencePath = relative(evidenceRoot, requestedPath);
    if (relativeEvidencePath.startsWith("..") || isAbsolute(relativeEvidencePath)) {
      response.statusCode = 403;
      response.end("Evidence path is outside the allowed evidence directory");
      return;
    }

    if (!existsSync(requestedPath)) {
      response.statusCode = 404;
      response.end("Evidence file not found");
      return;
    }

    response.setHeader("Content-Type", contentTypeFor(requestedPath));
    response.setHeader("Cache-Control", "no-store");
    createReadStream(requestedPath).pipe(response);
  }

  return {
    name: "local-evidence-dev-server",
    configureServer(server) {
      server.middlewares.use(handleEvidenceRequest);
    },
    configurePreviewServer(server) {
      server.middlewares.use(handleEvidenceRequest);
    },
  };
}

export default defineConfig({
  plugins: [react(), localEvidencePlugin()],
  server: {
    port: 5173,
    host: "0.0.0.0",
  },
  preview: {
    port: 4173,
    host: "0.0.0.0",
  },
});
