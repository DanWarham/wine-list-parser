import axios from "axios";
import { getSession } from "next-auth/react";

const API_BASE = "http://127.0.0.1:8000/api";

async function getAuthHeaders() {
  const session = await getSession();
  console.log('Session in getAuthHeaders:', session);
  if (!session?.accessToken) {
    throw new Error("No authentication token found");
  }
  return {
    Authorization: `Bearer ${session.accessToken}`,
    "Content-Type": "application/json"
  };
}

export async function apiGet(path) {
  try {
    const headers = await getAuthHeaders();
    const response = await axios.get(`${API_BASE}${path}`, { headers });
    return response;
  } catch (error) {
    if (error.message === "No authentication token found") {
      window.location.href = "/login";
    }
    if (error.response?.status === 401) {
      window.location.href = "/login";
    }
    throw error;
  }
}

export async function apiPost(path, data) {
  try {
    const headers = await getAuthHeaders();
    // If data is FormData, remove Content-Type so axios sets it automatically
    const finalHeaders = data instanceof FormData
      ? { ...headers }
      : headers;
    if (data instanceof FormData) {
      delete finalHeaders["Content-Type"];
    }
    const response = await axios.post(`${API_BASE}${path}`, data, { headers: finalHeaders });
    return response;
  } catch (error) {
    if (error.message === "No authentication token found") {
      window.location.href = "/login";
    }
    if (error.response?.status === 401) {
      window.location.href = "/login";
    }
    throw error;
  }
}

export async function apiPut(path, data) {
  try {
    const headers = await getAuthHeaders();
    const response = await axios.put(`${API_BASE}${path}`, data, { headers });
    return response;
  } catch (error) {
    if (error.message === "No authentication token found") {
      window.location.href = "/login";
    }
    if (error.response?.status === 401) {
      window.location.href = "/login";
    }
    throw error;
  }
}

export async function apiDelete(path) {
  try {
    const headers = await getAuthHeaders();
    const response = await axios.delete(`${API_BASE}${path}`, { headers });
    return response;
  } catch (error) {
    if (error.message === "No authentication token found") {
      window.location.href = "/login";
    }
    if (error.response?.status === 401) {
      window.location.href = "/login";
    }
    throw error;
  }
} 