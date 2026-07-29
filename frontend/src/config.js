// Production backend URL (Render deployment)
const RENDER_BACKEND_URL = 'https://medical-report-intelligence-system-mris.onrender.com';

// Dynamic API Base URL resolution:
// 1. Checks localStorage ('CUSTOM_API_URL')
// 2. Checks VITE_API_URL environment variable (set in GitHub Actions secret)
// 3. Falls back to Render backend if on GitHub Pages (not localhost)
// 4. Falls back to relative '' when running locally (same domain)
export function getApiBase() {
  const stored = typeof window !== 'undefined' ? localStorage.getItem('CUSTOM_API_URL') : null;
  const envUrl = import.meta.env.VITE_API_URL || '';
  const url = (stored || envUrl).trim();
  if (url) return url.replace(/\/$/, '');

  // Auto-detect: if not running on localhost, use Render backend
  if (typeof window !== 'undefined') {
    const host = window.location.hostname;
    if (host !== 'localhost' && host !== '127.0.0.1') {
      return RENDER_BACKEND_URL;
    }
  }
  return '';
}

export const API_BASE = getApiBase();

export function setCustomApiBase(url) {
  if (url && url.trim()) {
    localStorage.setItem('CUSTOM_API_URL', url.trim().replace(/\/$/, ''));
  } else {
    localStorage.removeItem('CUSTOM_API_URL');
  }
}

export async function safeFetchJson(endpoint, options = {}) {
  const apiBase = getApiBase();
  const url = `${apiBase}${endpoint}`;
  try {
    const response = await fetch(url, options);
    const contentType = response.headers.get("content-type") || "";

    if (!contentType.includes("application/json")) {
      const text = await response.text();
      if (response.status === 404 || text.includes("<!DOCTYPE html>") || text.includes("<html>")) {
        throw new Error(
          "Backend API is unreachable. Please open the Render app URL directly or click 'API Server' in the top header to set your backend URL."
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
      throw new Error("Cannot connect to Medical Report AI backend. Check if the server is running or set your API URL.");
    }
    throw err;
  }
}
