import axios from "axios";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE;

export function getAuthHeaders(token: string | undefined) {
  if (!token) {
    console.error("No authentication token found");
    throw new Error("No authentication token found");
  }
  return {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json"
  };
}

// Example usage in your API calls:
// const { session } = useAuth();
// const token = session?.access_token;
// const headers = getAuthHeaders(token);
// axios.get('/api/endpoint', { headers })

export async function apiGet(path: string, token: string) {
  try {
    const headers = getAuthHeaders(token);
    console.log("Making GET request to:", `${API_BASE}${path}`);
    const response = await axios.get(`${API_BASE}${path}`, { headers });
    return response;
  } catch (error: any) {
    console.error("API GET error:", error.response?.data || error.message);
    if (error.message === "No authentication token found") {
      window.location.href = "/login";
    }
    if (error.response?.status === 401) {
      window.location.href = "/login";
    }
    throw error;
  }
}

export async function apiPost(path: string, data: any, token: string) {
  try {
    const headers = getAuthHeaders(token);
    console.log("Making POST request to:", `${API_BASE}${path}`);
    const response = await axios.post(`${API_BASE}${path}`, data, { headers });
    return response;
  } catch (error: any) {
    console.error("API POST error:", error.response?.data || error.message);
    if (error.message === "No authentication token found") {
      window.location.href = "/login";
    }
    if (error.response?.status === 401) {
      window.location.href = "/login";
    }
    throw error;
  }
}

export async function apiPut(path: string, data: any, token: string) {
  try {
    const headers = getAuthHeaders(token);
    console.log("Making PUT request to:", `${API_BASE}${path}`);
    const response = await axios.put(`${API_BASE}${path}`, data, { headers });
    return response;
  } catch (error: any) {
    console.error("API PUT error:", error.response?.data || error.message);
    if (error.message === "No authentication token found") {
      window.location.href = "/login";
    }
    if (error.response?.status === 401) {
      window.location.href = "/login";
    }
    throw error;
  }
}

export async function apiDelete(path: string, token: string) {
  try {
    const headers = getAuthHeaders(token);
    console.log("Making DELETE request to:", `${API_BASE}${path}`);
    const response = await axios.delete(`${API_BASE}${path}`, { headers });
    return response;
  } catch (error: any) {
    console.error("API DELETE error:", error.response?.data || error.message);
    if (error.message === "No authentication token found") {
      window.location.href = "/login";
    }
    if (error.response?.status === 401) {
      window.location.href = "/login";
    }
    throw error;
  }
} 