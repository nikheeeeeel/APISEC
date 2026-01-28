import React from 'react';

const Disclaimer = () => {
  return (
    <div style={{
      padding: '16px',
      backgroundColor: '#fff3cd',
      border: '1px solid #ffc107',
      borderRadius: '4px',
      marginBottom: '24px',
    }}>
      <h3 style={{ marginTop: 0, color: '#856404' }}>⚠️ Disclaimer</h3>
      <p style={{ margin: '8px 0', color: '#856404', fontSize: '14px' }}>
        This documentation is automatically generated and provided on a <strong>best-effort basis</strong>.
        It may be incomplete or inaccurate. Auth-protected endpoints, dynamic endpoints, and non-GET
        endpoints may not be detected. Use at your own risk.
      </p>
    </div>
  );
};

export default Disclaimer;
