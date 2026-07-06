import React from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import TopBar from './TopBar';
import Breadcrumb from './Breadcrumb';
import SectionNav from './SectionNav';
import './Layout.css';

const FULL_BLEED_PATTERNS = [/\/board$/, /\/schedule$/];

// Script routes are /scenes/:id and /scripts/:id/:section — SectionNav renders for these only.
const deriveScriptId = (pathname) => {
  const scenes = pathname.match(/^\/scenes\/([^/]+)$/);
  if (scenes) return scenes[1];
  const section = pathname.match(/^\/scripts\/([^/]+)\/(?:stripboard|board|reports|schedule)/);
  return section ? section[1] : null;
};

const MainLayout = () => {
  const location = useLocation();
  const isFullBleed = FULL_BLEED_PATTERNS.some(p => p.test(location.pathname));
  const scriptId = deriveScriptId(location.pathname);

  return (
    <div className="main-layout no-sidebar">
      <TopBar />
      <Breadcrumb />
      {scriptId && <SectionNav scriptId={scriptId} />}
      <main className={`main-content${isFullBleed ? ' main-content--full-bleed' : ''}`}>
        <Outlet />
      </main>
    </div>
  );
};

export default MainLayout;
