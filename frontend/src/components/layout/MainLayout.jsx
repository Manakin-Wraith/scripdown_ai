import React from 'react';
import { Outlet } from 'react-router-dom';
import TopBar from './TopBar';
import Breadcrumb from './Breadcrumb';
import './Layout.css';

const MainLayout = () => {
  return (
    <div className="main-layout no-sidebar">
      <TopBar />
      <Breadcrumb />
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
};

export default MainLayout;
