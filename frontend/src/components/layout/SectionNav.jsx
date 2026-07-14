import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { List, ClipboardList, LayoutGrid, FileText, CalendarDays } from 'lucide-react';
import './SectionNav.css';

// `group` pairs consecutive tabs into a bordered segment (Board + Schedule
// are the same planning workflow). Reports is the output stage, so it sits
// last, after the scheduling cluster.
const SECTIONS = [
  { key: 'scenes', label: 'Scenes', icon: List, to: (id) => `/scenes/${id}` },
  { key: 'stripboard', label: 'Stripboard', icon: ClipboardList, to: (id) => `/scripts/${id}/stripboard` },
  { key: 'board', label: 'Board', icon: LayoutGrid, to: (id) => `/scripts/${id}/board`, group: 'plan' },
  { key: 'schedule', label: 'Schedule', icon: CalendarDays, to: (id) => `/scripts/${id}/schedule`, group: 'plan' },
  { key: 'reports', label: 'Reports', icon: FileText, to: (id) => `/scripts/${id}/reports` },
];

// Collapse consecutive same-group sections into { group, items } runs so a run
// can render inside a bordered wrapper; ungrouped tabs render on their own.
const groupSections = (sections) =>
  sections.reduce((runs, section) => {
    const last = runs[runs.length - 1];
    if (section.group && last?.group === section.group) {
      last.items.push(section);
    } else {
      runs.push({ group: section.group ?? null, items: [section] });
    }
    return runs;
  }, []);

// Active section derived from the URL only (not from ScriptContext).
const activeKey = (pathname) => {
  if (/^\/scenes\/[^/]+$/.test(pathname)) return 'scenes';
  const m = pathname.match(/^\/scripts\/[^/]+\/(stripboard|board|reports|schedule)/);
  return m ? m[1] : null;
};

const renderTab = ({ key, label, icon: Icon, to }, scriptId, active) => (
  <NavLink
    key={key}
    to={to(scriptId)}
    className={`section-nav-tab${active === key ? ' active' : ''}`}
  >
    <Icon size={16} />
    <span>{label}</span>
  </NavLink>
);

const SectionNav = ({ scriptId }) => {
  const { pathname } = useLocation();
  if (!scriptId) return null;
  const active = activeKey(pathname);

  return (
    <nav className="section-nav" aria-label="Script sections">
      {groupSections(SECTIONS).map((run) =>
        run.group ? (
          <div key={run.group} className="section-nav-group">
            {run.items.map((section) => renderTab(section, scriptId, active))}
          </div>
        ) : (
          run.items.map((section) => renderTab(section, scriptId, active))
        )
      )}
    </nav>
  );
};

export default SectionNav;
