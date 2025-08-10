import axios from 'axios';

// Types
export interface User {
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'staff';
  restaurant_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface Restaurant {
  id: string;
  name: string;
  wine_list_url: string | null;
  created_at: string;
  updated_at: string;
}

export interface WineList {
  id: string;
  restaurant_id: string;
  file_url: string;
  filename: string;
  status: 'uploaded' | 'processing' | 'parsed' | 'error';
  notes: string | null;
  created_at: string;
  updated_at: string;
  uploaded_at: string;
}

export interface WineListUploadResponse {
  id: string;
  status: string;
  message: string;
  learning_results?: any;
}

export interface WineEntry {
  id: string;
  wine_list_file_id: string;
  restaurant_id: string;
  producer: string | null;
  cuvee: string | null;
  type: string | null;
  vintage: string | null;
  price: string | null;
  bottle_size: string | null;
  grape_variety: string | null;
  country: string | null;
  region: string | null;
  subregion: string | null;
  row_confidence: number | null;
  field_confidence: any | null;
  section_header: string | null;
  subheader: string | null;
  raw_text: string | null;
  status: 'auto' | 'user_edited' | 'confirmed' | 'rejected';
  designation: string | null;
  classification: string | null;
  sub_type: string | null;
  extra_data: any | null;
  last_modified: string;
}

export interface Ruleset {
  id: string;
  name: string;
  rules: Record<string, any>;
  created_at: string;
  updated_at: string;
}

// API Configuration
const API_BASE = '/api/v2';

// Helper Functions
function getAuthHeaders(token: string) {
  return {
    Authorization: `Bearer ${token}`,
    'Content-Type': 'application/json',
  };
}

// Error Handling
export class APIError extends Error {
  constructor(
    message: string,
    public status?: number,
    public data?: any
  ) {
    super(message);
    this.name = 'APIError';
  }
}

async function handleError(error: any): Promise<never> {
  if (axios.isAxiosError(error)) {
    const message = error.response?.data?.detail || error.message;
    throw new APIError(message, error.response?.status, error.response?.data);
  }
  throw error;
}

// API Functions
export const api = {
  // User Management
  async getCurrentUser(token: string): Promise<User> {
    try {
      const response = await axios.get(`${API_BASE}/me`, {
        headers: getAuthHeaders(token),
      });
      return response.data;
    } catch (error) {
      return handleError(error);
    }
  },

  async createUser(token: string, data: Omit<User, 'id' | 'created_at' | 'updated_at'>): Promise<User> {
    try {
      const response = await axios.post(`${API_BASE}/users`, data, {
        headers: getAuthHeaders(token),
      });
      return response.data;
    } catch (error) {
      return handleError(error);
    }
  },

  async getUsers(token: string): Promise<User[]> {
    try {
      const response = await axios.get(`${API_BASE}/users`, {
        headers: getAuthHeaders(token),
      });
      return response.data;
    } catch (error) {
      return handleError(error);
    }
  },

  async updateUser(token: string, userId: string, data: Partial<User>): Promise<User> {
    try {
      const response = await axios.put(`${API_BASE}/users/${userId}`, data, {
        headers: getAuthHeaders(token),
      });
      return response.data;
    } catch (error) {
      return handleError(error);
    }
  },

  async deleteUser(token: string, userId: string): Promise<void> {
    try {
      await axios.delete(`${API_BASE}/users/${userId}`, {
        headers: getAuthHeaders(token),
      });
    } catch (error) {
      return handleError(error);
    }
  },

  // Restaurant Management
  async getRestaurants(token: string): Promise<Restaurant[]> {
    try {
      const response = await axios.get(`${API_BASE}/restaurants`, {
        headers: getAuthHeaders(token),
      });
      return response.data;
    } catch (error) {
      return handleError(error);
    }
  },

  async createRestaurant(token: string, data: Omit<Restaurant, 'id' | 'created_at' | 'updated_at'>): Promise<Restaurant> {
    try {
      const response = await axios.post(`${API_BASE}/restaurants`, data, {
        headers: getAuthHeaders(token),
      });
      return response.data;
    } catch (error) {
      return handleError(error);
    }
  },

  async updateRestaurant(token: string, restaurantId: string, data: Partial<Restaurant>): Promise<Restaurant> {
    try {
      const response = await axios.put(`${API_BASE}/restaurants/${restaurantId}`, data, {
        headers: getAuthHeaders(token),
      });
      return response.data;
    } catch (error) {
      return handleError(error);
    }
  },

  async deleteRestaurant(token: string, restaurantId: string): Promise<void> {
    try {
      await axios.delete(`${API_BASE}/restaurants/${restaurantId}`, {
        headers: getAuthHeaders(token),
      });
    } catch (error) {
      return handleError(error);
    }
  },

  // Wine List Management
  async getWineLists(token: string, restaurantId?: string): Promise<WineList[]> {
    try {
      const url = restaurantId
        ? `${API_BASE}/restaurants/${restaurantId}/wine-lists`
        : `${API_BASE}/wine-lists`;
      const response = await axios.get(url, {
        headers: getAuthHeaders(token),
      });
      return response.data;
    } catch (error) {
      return handleError(error);
    }
  },

  async getProcessingSteps(token: string, fileId: string): Promise<any> {
    try {
      const response = await axios.get(`${API_BASE}/wine-lists/${fileId}/processing-steps`, {
        headers: getAuthHeaders(token),
      });
      return response.data;
    } catch (error) {
      return handleError(error);
    }
  },

  async uploadWineList(
    token: string, 
    restaurantId: string, 
    file: File, 
    onProgress?: (progress: number) => void
  ): Promise<WineListUploadResponse> {
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('restaurant_id', restaurantId);
      
      const config: any = {
        headers: {
          ...getAuthHeaders(token),
          'Content-Type': 'multipart/form-data',
        },
        timeout: 300000, // 5 minute timeout for large files
      };
      
      // Add progress tracking if callback provided
      if (onProgress) {
        config.onUploadProgress = (progressEvent: any) => {
          if (progressEvent.total) {
            const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            onProgress(progress);
          }
        };
      }
      
      const response = await axios.post(`${API_BASE}/wine-lists/upload`, formData, config);
      return response.data;
    } catch (error) {
      return handleError(error);
    }
  },

  async deleteWineList(token: string, wineListId: string): Promise<void> {
    try {
      await axios.delete(`${API_BASE}/wine-lists/${wineListId}`, {
        headers: getAuthHeaders(token),
      });
    } catch (error) {
      return handleError(error);
    }
  },

  async reprocessWineList(token: string, wineListId: string): Promise<void> {
    try {
      await axios.post(`${API_BASE}/wine-lists/${wineListId}/reprocess`, {}, {
        headers: getAuthHeaders(token),
      });
    } catch (error) {
      return handleError(error);
    }
  },

  // Wine Entry Management
  async getWineEntries(token: string, wineListId: string): Promise<WineEntry[]> {
    try {
      const response = await axios.get(`${API_BASE}/wine-entries/${wineListId}`, {
        headers: getAuthHeaders(token),
      });
      return response.data;
    } catch (error) {
      return handleError(error);
    }
  },

  async updateWineEntry(token: string, entryId: string, data: Partial<WineEntry>): Promise<WineEntry> {
    try {
      const response = await axios.put(`${API_BASE}/wine-entries/${entryId}`, data, {
        headers: getAuthHeaders(token),
      });
      return response.data;
    } catch (error) {
      return handleError(error);
    }
  },

  async bulkUpdateWineEntries(token: string, entries: Array<{ id: string } & Partial<WineEntry>>): Promise<WineEntry[]> {
    try {
      const response = await axios.put(`${API_BASE}/wine-entries/bulk`, entries, {
        headers: getAuthHeaders(token),
      });
      return response.data;
    } catch (error) {
      return handleError(error);
    }
  },

  // Ruleset Management
  async getRuleset(token: string): Promise<Ruleset> {
    try {
      const response = await axios.get(`${API_BASE}/ruleset`, {
        headers: getAuthHeaders(token),
      });
      return response.data;
    } catch (error) {
      return handleError(error);
    }
  },

  async updateRuleset(token: string, data: Partial<Ruleset>): Promise<Ruleset> {
    try {
      const response = await axios.put(`${API_BASE}/ruleset`, data, {
        headers: getAuthHeaders(token),
      });
      return response.data;
    } catch (error) {
      return handleError(error);
    }
  },

  async clearRestaurantRules(token: string, restaurantId: string): Promise<void> {
    try {
      await axios.delete(`${API_BASE}/restaurants/${restaurantId}/ruleset`, {
        headers: getAuthHeaders(token),
      });
    } catch (error) {
      return handleError(error);
    }
  },
}; 