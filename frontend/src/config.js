// API configuration: use VITE_API_URL environment variable if set, otherwise relative path
export const API_BASE = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '');

export async function safeFetchJson(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  try {
    const response = await fetch(url, options);
    const contentType = response.headers.get("content-type") || "";

    if (!contentType.includes("application/json")) {
      const text = await response.text();
      if (response.status === 404 || text.includes("<!DOCTYPE html>") || text.includes("<html>")) {
        throw new Error(
          "Backend API is unreachable. Please start the Python backend server (`py backend/app.py`) or configure VITE_API_URL."
        );
      }
      throw new Error(`Server returned non-JSON response (Status ${response.status})`);
    }

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || data.message || `Error ${response.status}: Request failed`);
    }

    return data;
  } catch (err) {
    if (err.name === "TypeError" && err.message.includes("fetch")) {
      throw new Error("Cannot connect to Medical Report AI backend. Check if the server is running.");
    }
    throw err;
  }
}
