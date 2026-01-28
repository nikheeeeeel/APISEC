import React from 'react';
import ReactDOM from 'react-dom/client';
import GenerateDocs from './pages/GenerateDocs';
import './index.css';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <GenerateDocs />
  </React.StrictMode>
);
