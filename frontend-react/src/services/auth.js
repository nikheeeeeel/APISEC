const API_BASE_URL = 'http://localhost:8001';

class AuthService {
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

  // Store token in localStorage
  static setToken(token) {
    localStorage.setItem('access_token', token);
  }

  // Get token from localStorage
  static getToken() {
    return localStorage.getItem('access_token');
  }

  // Remove token from localStorage
  static removeToken() {
    localStorage.removeItem('access_token');
  }

  // Check if user is logged in
  static isLoggedIn() {
    return !!this.getToken();
  }

  // Get Authorization header
  static getAuthHeader() {
    const token = this.getToken();
    return token ? { 'Authorization': `Bearer ${token}` } : {};
  }

  // Register new user
  static async register(userData) {
    return this.request(`${API_BASE_URL}/auth/register`, {
      method: 'POST',
      body: JSON.stringify(userData)
    });
  }

  // Login user
  static async login(credentials) {
    return this.request(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      body: JSON.stringify(credentials)
    });
  }

  // Get current user info
  static async getCurrentUser() {
    return this.request(`${API_BASE_URL}/auth/me`, {
      headers: {
        ...this.getAuthHeader()
      }
    });
  }

  // OAuth login URLs
  static getGoogleOAuthUrl() {
    return `${API_BASE_URL}/auth/oauth/google`;
  }

  static getGitHubOAuthUrl() {
    return `${API_BASE_URL}/auth/oauth/github`;
  }

  // Handle OAuth callback
  static handleOAuthCallback(token) {
    this.setToken(token);
    return token;
  }

  // Logout
  static logout() {
    this.removeToken();
    // You could also call a backend logout endpoint if needed
  }
}

export default AuthService;
