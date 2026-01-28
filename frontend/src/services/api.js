/** API service for communicating with backend */
const API_BASE_URL = 'http://localhost:8000/api';

export const apiService = {
  /**
   * Generate API documentation
   * @param {string} apiUri - Target API URI
   * @param {string|null} apiKey - Optional API key
   * @param {string|null} bearerToken - Optional bearer token
   * @returns {Promise<Object>} Response data
   */
  async generateDocs(apiUri, apiKey = null, bearerToken = null) {
    const response = await fetch(`${API_BASE_URL}/generate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        api_uri: apiUri,
        api_key: apiKey || null,
        bearer_token: bearerToken || null,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to generate documentation');
    }

    return response.json();
  },

  /**
   * List all generated reports
   * @returns {Promise<Array>} List of reports
   */
  async listReports() {
    const response = await fetch(`${API_BASE_URL}/reports`);

    if (!response.ok) {
      throw new Error('Failed to fetch reports');
    }

    const data = await response.json();
    return data.reports;
  },

  /**
   * Download a report
   * @param {string} reportId - Report ID/filename
   * @returns {string} Download URL
   */
  getReportDownloadUrl(reportId) {
    return `${API_BASE_URL}/reports/${reportId}`;
  },
};
