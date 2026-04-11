const API_BASE_URL = import.meta.env.VITE_API_BASE || "";

export async function generateMagicImage({ file, style }) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("style", style);

  const response = await fetch(`${API_BASE_URL}/generate`, {
    method: "POST",
    body: formData
  });

  let payload;
  try {
    payload = await response.json();
  } catch (error) {
    throw new Error("The server returned an unreadable response.");
  }

  if (!response.ok) {
    throw new Error(payload?.detail || "Image generation failed.");
  }

  return payload;
}
