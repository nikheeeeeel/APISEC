import React, { useState, useEffect } from 'react';
import './LandingPage.css';

const LandingPage = ({ onGetStarted }) => {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    setIsVisible(true);
  }, []);

  const features = [
    {
      icon: '🔍',
      title: 'Schema Discovery',
      description: 'Automatically discover and analyze API schemas from any endpoint',
      color: '#0066ff'
    },
    {
      icon: '✅',
      title: 'Runtime Validation',
      description: 'Test API endpoints against documented schemas in real-time',
      color: '#00d4aa'
    },
    {
      icon: '📚',
      title: 'Version History',
      description: 'Track and compare API schema changes over time',
      color: '#ff6b6b'
    },
    {
      icon: '🚀',
      title: 'Modern Interface',
      description: 'Sleek dark theme with smooth animations and interactions',
      color: '#9c88ff'
    }
  ];

  const stats = [
    { number: '50+', label: 'API Formats' },
    { number: '100%', label: 'Accuracy' },
    { number: '< 1s', label: 'Response Time' }
  ];

  return (
    <div className={`landing-page ${isVisible ? 'visible' : ''}`}>
      {/* Hero Section */}
      <section className="hero">
        <div className="hero-content">
          <div className="hero-text">
            <h1 className="hero-title">
              <span className="gradient-text">API Security</span>
              <br />
              Testing Platform
            </h1>
            <p className="hero-subtitle">
              Discover, validate, and monitor API schemas with our modern testing suite
            </p>
            <div className="hero-buttons">
              <button className="btn-primary" onClick={onGetStarted}>
                Get Started
                <span className="btn-arrow">→</span>
              </button>
              <button className="btn-secondary">
                View Documentation
              </button>
            </div>
          </div>
          <div className="hero-visual">
            <div className="floating-card">
              <div className="card-header">
                <div className="card-dots">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
              <div className="card-content">
                <div className="code-line">
                  <span className="code-keyword">GET</span>
                  <span className="code-url">/api/users</span>
                </div>
                <div className="code-line">
                  <span className="code-status">200</span>
                  <span className="code-success">✓ Valid</span>
                </div>
              </div>
            </div>
            <div className="floating-elements">
              <div className="element element-1"></div>
              <div className="element element-2"></div>
              <div className="element element-3"></div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="features">
        <div className="container">
          <h2 className="section-title">Powerful Features</h2>
          <div className="features-grid">
            {features.map((feature, index) => (
              <div 
                key={index} 
                className="feature-card"
                style={{ '--accent-color': feature.color }}
              >
                <div className="feature-icon">{feature.icon}</div>
                <h3 className="feature-title">{feature.title}</h3>
                <p className="feature-description">{feature.description}</p>
                <div className="feature-glow"></div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="stats">
        <div className="container">
          <div className="stats-grid">
            {stats.map((stat, index) => (
              <div key={index} className="stat-card">
                <div className="stat-number">{stat.number}</div>
                <div className="stat-label">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="cta">
        <div className="container">
          <div className="cta-content">
            <h2 className="cta-title">Ready to Secure Your APIs?</h2>
            <p className="cta-description">
              Join thousands of developers who trust our platform for API testing and validation
            </p>
            <button className="btn-primary btn-large" onClick={onGetStarted}>
              Start Testing Now
              <span className="btn-arrow">→</span>
            </button>
          </div>
        </div>
      </section>
    </div>
  );
};

export default LandingPage;
