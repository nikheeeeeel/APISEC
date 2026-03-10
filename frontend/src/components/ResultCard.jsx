import React from 'react';

const ResultCard = ({ title, children, type = 'default' }) => {
  const cardClass = type === 'error' ? 'error' : type === 'success' ? 'schema-info' : 'result';
  
  return (
    <div className={cardClass}>
      {title && <h3>{title}</h3>}
      {children}
    </div>
  );
};

export default ResultCard;
