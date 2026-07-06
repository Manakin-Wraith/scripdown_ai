import React from 'react';
import './PageHeader.css';

const PageHeader = ({ title, subtitle, icon, actions }) => (
  <header className="page-header">
    <div className="page-header-text">
      <h1 className="page-header-title">
        {icon && <span className="page-header-icon">{icon}</span>}
        {title}
      </h1>
      {subtitle && <p className="page-header-subtitle">{subtitle}</p>}
    </div>
    {actions && <div className="page-header-actions">{actions}</div>}
  </header>
);

export default PageHeader;
