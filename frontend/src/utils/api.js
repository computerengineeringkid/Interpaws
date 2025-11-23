export async function parseErrorResponse(response) {
  try {
    return await response.json();
  } catch (jsonError) {
    try {
      const text = await response.text();
      if (text) {
        return { detail: text };
      }
    } catch (textError) {
      // Ignore secondary parsing errors
    }
    return { detail: "Unexpected server response" };
  }
}
