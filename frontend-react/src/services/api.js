const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8001';

class ApiService {
  static getAuthHeader() {
    const token = localStorage.getItem('access_token');
    return token ? { 'Authorization': `Bearer ${token}` } : {};
  }

  static async handleResponse(response) {
    const data = await response.json();
    
    if (!response.ok) {
      if (response.status === 401) {
        localStorage.removeItem('access_token');
        window.location.hash = '#/login'; // Simple redirect strategy
      }
      throw new Error(data.detail || data.error || `HTTP error! status: ${response.status}`);
    }
    
    return data;
  }

  static async request(url, options = {}) {
    try {
      const response = await fetch(url, {
        headers: {
          'Content-Type': 'application/json',
          ...this.getAuthHeader(),
          ...options.headers
        },
        ...options
      });
      
      return await this.handleResponse(response);
    } catch (error) {
      if (error.name === 'TypeError' && error.message.includes('Failed to fetch')) {
        throw new Error('Unable to connect to the backend. Please ensure the backend server is running on http://127.0.0.1:8001');
      }
      throw error;
    }
  }

  // Auth endpoints
  static async login(username, password) {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);
    
    try {
      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: 'POST',
        body: formData
      });
      const data = await this.handleResponse(response);
      localStorage.setItem('access_token', data.access_token);
      return data;
    } catch (error) {
      throw error;
    }
  }

  static async register(username, password) {
    return this.request(`${API_BASE_URL}/auth/register`, {
      method: 'POST',
      body: JSON.stringify({ username, password })
    });
  }

  static logout() {
    localStorage.removeItem('access_token');
    window.location.hash = '#/login';
  }

  static isAuthenticated() {
    return !!localStorage.getItem('access_token');
  }

  // API Registry endpoints
  static async getApis() {
    return this.request(`${API_BASE_URL}/api/apis`);
  }

  static async createApi(name, base_url, description = null) {
    const formData = new FormData();
    formData.append('name', name);
    formData.append('base_url', base_url);
    if (description) {
      formData.append('description', description);
    }

    try {
      const response = await fetch(`${API_BASE_URL}/api/apis`, {
        method: 'POST',
        headers: { ...this.getAuthHeader() },
        body: formData
      });
      
      return await this.handleResponse(response);
    } catch (error) {
      if (error.name === 'TypeError' && error.message.includes('Failed to fetch')) {
        throw new Error('Unable to connect to the backend. Please ensure the backend server is running on http://127.0.0.1:8001');
      }
      throw error;
    }
  }

  static async deleteApi(apiId) {
    return this.request(`${API_BASE_URL}/api/apis/${apiId}`, {
      method: 'DELETE'
    });
  }

  // Schema endpoints
  static async getApiSchemas(apiId) {
    return this.request(`${API_BASE_URL}/api/apis/${apiId}/schemas`);
  }

  static async getLatestSchema(apiId) {
    return this.request(`${API_BASE_URL}/api/apis/${apiId}/schemas/latest`);
  }

  static async getSchemaVersion(apiId, version) {
    return this.request(`${API_BASE_URL}/api/schemas/${apiId}/version/${version}`);
  }

  static async scanApiSchema(apiId) {
    return this.request(`${API_BASE_URL}/api/apis/${apiId}/scan`, {
      method: 'POST'
    });
  }

  static async compareSchemaVersions(apiId, version1, version2, structured = true) {
    return this.request(`${API_BASE_URL}/api/schemas/${apiId}/compare/${version1}/${version2}?structured=${structured}`);
  }

  static async analyzeChange(apiId, version1, version2, change) {
    return this.request(`${API_BASE_URL}/api/schemas/${apiId}/analyze-change`, {
      method: 'POST',
      body: JSON.stringify({ version1, version2, change })
    });
  }

  // Schema discovery endpoint
  static async discoverSchema(url) {
    return this.request(`${API_BASE_URL}/discover-schema`, {
      method: 'POST',
      body: JSON.stringify({ url })
    });
  }

  // Runtime validation endpoint
  static async validateRuntime(baseUrl, schemaInfo) {
    return this.request(`${API_BASE_URL}/validate-runtime`, {
      method: 'POST',
      body: JSON.stringify({ base_url: baseUrl, schema_info: schemaInfo })
    });
  }
}

export default ApiService;
