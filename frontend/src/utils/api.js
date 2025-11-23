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