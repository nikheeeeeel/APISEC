import React, { useState } from 'react';
import ApiForm from '../components/ApiForm';
import Disclaimer from '../components/Disclaimer';
import ReportsList from '../components/ReportsList';

const GenerateDocs = () => {
  const [successMessage, setSuccessMessage] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);

  const handleSuccess = (result) => {
    setSuccessMessage(
      `Documentation generated successfully via ${result.discovery_method} method!`
    );
    setErrorMessage(null);
    
    // Clear success message after 5 seconds
    setTimeout(() => setSuccessMessage(null), 5000);
  };

  const handleError = (error) => {
    setErrorMessage(error);
    setSuccessMessage(null);
    
    // Clear error message after 5 seconds
    setTimeout(() => setErrorMessage(null), 5000);
  };

  return (
    <div style={{
      maxWidth: '900px',
      margin: '0 auto',
      padding: '24px',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    }}>
      <header style={{ marginBottom: '32px', textAlign: 'center' }}>
        <h1 style={{ margin: 0, fontSize: '32px', color: '#333' }}>
          APISEC v1
        </h1>
        <p style={{ margin: '8px 0', color: '#6c757d', fontSize: '16px' }}>
          Automated OpenAPI Documentation Generator
        </p>
      </header>

      <Disclaimer />

      <section style={{ marginBottom: '48px' }}>
        <h2 style={{ fontSize: '24px', marginBottom: '16px' }}>Generate Documentation</h2>
        
        {successMessage && (
          <div style={{
            padding: '12px',
            backgroundColor: '#d4edda',
            border: '1px solid #c3e6cb',
            borderRadius: '4px',
            color: '#155724',
            marginBottom: '16px',
          }}>
            {successMessage}
          </div>
        )}

        {errorMessage && (
          <div style={{
            padding: '12px',
            backgroundColor: '#f8d7da',
            border: '1px solid #f5c6cb',
            borderRadius: '4px',
            color: '#721c24',
            marginBottom: '16px',
          }}>
            {errorMessage}
          </div>
        )}

        <ApiForm onSuccess={handleSuccess} onError={handleError} />
      </section>

      <section>
        <ReportsList />
      </section>
    </div>
  );
};

export default GenerateDocs;
