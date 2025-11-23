export async function parseErrorResponse(response) {
  try {
    // Try to parse as JSON first
    return await response.json();
  } catch (jsonError) {
    // If JSON fails, get the text (likely HTML error)
    try {
      const text = await response.text();
      console.error("API Error (Non-JSON):", text); // <--- Log the real error to console
      if (text) {
        // If it's a 404 HTML page, return a clearer message
        if (text.includes("<!DOCTYPE html>")) {
          return { detail: `Server endpoint not found (${response.status}). Check next.config.mjs rewrites.` };
        }
        return { detail: text };
      }
    } catch (textError) {
      // Ignore secondary parsing errors
    }
    return { detail: `Unexpected server response (${response.status})` };
  }
}

/**
 * Fetch wrapper with automatic token refresh on 401 responses.
 *
 * @param {string} url - The URL to fetch
 * @param {object} options - Fetch options (method, body, headers, etc.)
 * @returns {Promise<Response>} - The fetch response
 */
export async function fetchWithAuth(url, options = {}) {
  // Get current access token
  const token = localStorage.getItem("interpaws_auth_token");

  // Set up headers with Authorization if token exists
  if (token) {
    options.headers = {
      ...options.headers,
      Authorization: `Bearer ${token}`,
    };
  }

  // Make the initial request
  let response = await fetch(url, options);

  // If 401 Unauthorized, attempt to refresh the token
  if (response.status === 401) {
    const refreshToken = localStorage.getItem("interpaws_refresh_token");

    if (!refreshToken) {
      // No refresh token available, clear storage and redirect
      localStorage.removeItem("interpaws_auth_token");
      localStorage.removeItem("interpaws_auth_user");
      localStorage.removeItem("interpaws_auth_role");
      localStorage.removeItem("interpaws_refresh_token");
      window.location.href = "/login";
      throw new Error("Session expired. Please log in again.");
    }

    try {
      // Attempt to refresh the access token
      const refreshResponse = await fetch("/api/refresh", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (refreshResponse.ok) {
        const refreshData = await refreshResponse.json();
        const newAccessToken = refreshData.access_token;

        // Save the new access token
        localStorage.setItem("interpaws_auth_token", newAccessToken);

        // Update the Authorization header for the retry
        options.headers = {
          ...options.headers,
          Authorization: `Bearer ${newAccessToken}`,
        };

        // Retry the original request with the new token
        response = await fetch(url, options);
      } else {
        // Refresh failed, clear storage and redirect
        localStorage.removeItem("interpaws_auth_token");
        localStorage.removeItem("interpaws_auth_user");
        localStorage.removeItem("interpaws_auth_role");
        localStorage.removeItem("interpaws_refresh_token");
        window.location.href = "/login";
        throw new Error("Session expired. Please log in again.");
      }
    } catch (error) {
      // Network error during refresh, clear storage and redirect
      localStorage.removeItem("interpaws_auth_token");
      localStorage.removeItem("interpaws_auth_user");
      localStorage.removeItem("interpaws_auth_role");
      localStorage.removeItem("interpaws_refresh_token");
      window.location.href = "/login";
      throw new Error("Session expired. Please log in again.");
    }
  }

  return response;
}