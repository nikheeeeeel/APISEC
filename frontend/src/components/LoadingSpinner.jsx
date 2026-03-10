import React from 'react';

const LoadingSpinner = ({ size = 'medium' }) => {
  const sizeClass = size === 'small' ? 'spinner-small' : size === 'large' ? 'spinner-large' : 'spinner-medium';
  
  return (
    <div className="loading">
      <div className={`spinner ${sizeClass}`}></div>
      <p>Processing...</p>
    </div>
  );
};

export default LoadingSpinner;
