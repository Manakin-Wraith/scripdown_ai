import React from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import TopBar from './TopBar';
import Breadcrumb from './Breadcrumb';
import './Layout.css';

const FULL_BLEED_PATTERNS = [/\/board$/, /\/schedule$/];

const MainLayout = () => {
  const location = useLocation();
  const isFullBleed = FULL_BLEED_PATTERNS.some(p => p.test(location.pathname));

  return (
    <div className="main-layout no-sidebar">
      <TopBar />
      <Breadcrumb />
      <main className={`main-content${isFullBleed ? ' main-content--full-bleed' : ''}`}>
        <Outlet />
      </main>
    </div>
  );
};

export default MainLayout;
