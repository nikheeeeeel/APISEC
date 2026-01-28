import React, { useState, useEffect } from 'react';
import { apiService } from '../services/api';

const ReportsList = () => {
  const [reports, setReports] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadReports = async () => {
    try {
      setIsLoading(true);
      const reportsList = await apiService.listReports();
      setReports(reportsList);
      setError(null);
    } catch (err) {
      setError(err.message || 'Failed to load reports');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadReports();
  }, []);

  const formatDate = (dateString) => {
    try {
      const date = new Date(dateString);
      return date.toLocaleString();
    } catch {
      return dateString;
    }
  };

  const getDiscoveryBadge = (method) => {
    const color = method === 'existing' ? '#28a745' : '#ffc107';
    const text = method === 'existing' ? 'Existing Spec' : 'Inferred';
    return (
      <span style={{
        padding: '4px 8px',
        borderRadius: '4px',
        backgroundColor: color,
        color: 'white',
        fontSize: '12px',
        fontWeight: 'bold',
      }}>
        {text}
      </span>
    );
  };

  if (isLoading) {
    return <div style={{ padding: '20px', textAlign: 'center' }}>Loading reports...</div>;
  }

  if (error) {
    return (
      <div style={{ padding: '20px', color: '#dc3545' }}>
        Error: {error}
        <button onClick={loadReports} style={{ marginLeft: '12px', padding: '4px 8px' }}>
          Retry
        </button>
      </div>
    );
  }

  if (reports.length === 0) {
    return (
      <div style={{ padding: '20px', textAlign: 'center', color: '#6c757d' }}>
        No reports generated yet. Generate your first documentation above!
      </div>
    );
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <h2 style={{ margin: 0 }}>Generated Reports</h2>
        <button
          onClick={loadReports}
          style={{
            padding: '8px 16px',
            fontSize: '14px',
            backgroundColor: '#6c757d',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
          }}
        >
          Refresh
        </button>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {reports.map((report) => (
          <div
            key={report.id}
            style={{
              padding: '16px',
              border: '1px solid #ddd',
              borderRadius: '4px',
              backgroundColor: '#f8f9fa',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
              <div>
                <h3 style={{ margin: 0, fontSize: '16px', marginBottom: '4px' }}>
                  {report.filename}
                </h3>
                <p style={{ margin: '4px 0', fontSize: '14px', color: '#6c757d' }}>
                  {report.api_uri}
                </p>
                <p style={{ margin: '4px 0', fontSize: '12px', color: '#6c757d' }}>
                  Generated: {formatDate(report.generated_at)}
                </p>
              </div>
              <div>
                {getDiscoveryBadge(report.discovery_method)}
              </div>
            </div>
            <a
              href={apiService.getReportDownloadUrl(report.id)}
              download={report.filename}
              style={{
                display: 'inline-block',
                padding: '8px 16px',
                backgroundColor: '#007bff',
                color: 'white',
                textDecoration: 'none',
                borderRadius: '4px',
                fontSize: '14px',
              }}
            >
              Download PDF
            </a>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ReportsList;
