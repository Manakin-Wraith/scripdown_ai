import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { List, ClipboardList, LayoutGrid, FileText, CalendarDays } from 'lucide-react';
import './SectionNav.css';

const SECTIONS = [
  { key: 'scenes', label: 'Scenes', icon: List, to: (id) => `/scenes/${id}` },
  { key: 'stripboard', label: 'Stripboard', icon: ClipboardList, to: (id) => `/scripts/${id}/stripboard` },
  { key: 'board', label: 'Board', icon: LayoutGrid, to: (id) => `/scripts/${id}/board` },
  { key: 'reports', label: 'Reports', icon: FileText, to: (id) => `/scripts/${id}/reports` },
  { key: 'schedule', label: 'Schedule', icon: CalendarDays, to: (id) => `/scripts/${id}/schedule` },
];

// Active section derived from the URL only (not from ScriptContext).
const activeKey = (pathname) => {
  if (/^\/scenes\/[^/]+$/.test(pathname)) return 'scenes';
  const m = pathname.match(/^\/scripts\/[^/]+\/(stripboard|board|reports|schedule)/);
  return m ? m[1] : null;
};

const SectionNav = ({ scriptId }) => {
  const { pathname } = useLocation();
  if (!scriptId) return null;
  const active = activeKey(pathname);

  return (
    <nav className="section-nav" aria-label="Script sections">
      {SECTIONS.map(({ key, label, icon: Icon, to }) => (
        <NavLink
          key={key}
          to={to(scriptId)}
          className={`section-nav-tab${active === key ? ' active' : ''}`}
        >
          <Icon size={16} />
          <span>{label}</span>
        </NavLink>
      ))}
    </nav>
  );
};

export default SectionNav;
