import React from 'react';

const ParameterTable = ({ parameters, onChange, onAdd, onRemove }) => {
  const updateParam = (index, field, value) => {
    const updated = [...parameters];
    updated[index][field] = value;
    onChange(updated);
  };

  return (
    <div className="params-table">
      <div style={{
        display: 'grid', 
        gridTemplateColumns: '1fr 1fr 2fr 40px', 
        gap: '12px', 
        padding: '12px', 
        background: 'var(--bg-tertiary)', 
        borderRadius: 'var(--radius-md)', 
        marginBottom: '12px'
      }}>
        <strong style={{color: 'var(--text-primary)', fontSize: '12px', fontWeight: '600'}}>Key</strong>
        <strong style={{color: 'var(--text-primary)', fontSize: '12px', fontWeight: '600'}}>Value</strong>
        <strong style={{color: 'var(--text-primary)', fontSize: '12px', fontWeight: '600'}}>Description</strong>
        <span></span>
      </div>
      
      {parameters.map((param, index) => (
        <div key={index} className="param-row">
          <div className="params-grid">
            <input 
              className="param-input focus-ring"
              value={param.key}
              onChange={(e) => updateParam(index, 'key', e.target.value)}
              type="text" 
              placeholder="Key"
            />
            <input 
              className="param-input focus-ring"
              value={param.value}
              onChange={(e) => updateParam(index, 'value', e.target.value)}
              type="text" 
              placeholder="Value"
            />
            <input 
              className="param-input focus-ring"
              value={param.description}
              onChange={(e) => updateParam(index, 'description', e.target.value)}
              type="text" 
              placeholder="Description"
            />
            <button 
              className="remove-btn"
              onClick={() => onRemove(index)}
              aria-label="Remove parameter"
            >
              ×
            </button>
          </div>
        </div>
      ))}
      
      <button 
        className="btn" 
        onClick={onAdd}
        style={{marginTop: '12px', padding: '8px 16px', fontSize: '13px'}}
      >
        + Add Parameter
      </button>
    </div>
  );
};

export default ParameterTable;
