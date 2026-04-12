function resolveApiBaseUrl() {
  const configuredBaseUrl = import.meta.env.VITE_API_BASE?.trim();
  if (configuredBaseUrl) {
    return configuredBaseUrl.replace(/\/$/, "");
  }

  if (typeof window === "undefined") {
    return "";
  }

  const { hostname, origin } = window.location;
  const isLocalhost = hostname === "localhost" || hostname === "127.0.0.1";

  if (isLocalhost) {
    return "http://localhost:8080";
  }

  return origin;
}

const API_BASE_URL = resolveApiBaseUrl();

async function readJsonResponse(response) {
  try {
    return await response.json();
  } catch (error) {
    throw new Error("The server returned an unreadable response.");
  }
}

export async function fetchHealth() {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}/health`);
  } catch (error) {
    throw new Error("Could not reach the backend service.");
  }

  if (!response.ok) {
    throw new Error("Could not load service health.");
  }

  return readJsonResponse(response);
}

export async function generateMagicImage({ file, style }) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("style", style);

  let response;
  try {
    response = await fetch(`${API_BASE_URL}/generate`, {
      method: "POST",
      body: formData
    });
  } catch (error) {
    throw new Error("Could not reach the backend service.");
  }

  const payload = await readJsonResponse(response);

  if (!response.ok) {
    throw new Error(payload?.detail || "Image generation failed.");
  }

  return payload;
}
