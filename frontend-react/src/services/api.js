const API_BASE_URL = 'http://localhost:8001';

class ApiService {
  static async handleResponse(response) {
    const data = await response.json();
    
    if (!response.ok) {
      throw new Error(data.error || `HTTP error! status: ${response.status}`);
    }
    
    return data;
  }

  static async request(url, options = {}) {
    try {
      const response = await fetch(url, {
        headers: {
          'Content-Type': 'application/json',
          ...options.headers
        },
        ...options
      });
      
      return await this.handleResponse(response);
    } catch (error) {
      if (error.name === 'TypeError' && error.message.includes('Failed to fetch')) {
        throw new Error('Unable to connect to the backend. Please ensure the backend server is running on http://localhost:8001');
      }
      throw error;
    }
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
        body: formData
      });
      
      return await this.handleResponse(response);
    } catch (error) {
      if (error.name === 'TypeError' && error.message.includes('Failed to fetch')) {
        throw new Error('Unable to connect to the backend. Please ensure the backend server is running on http://localhost:8001');
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
