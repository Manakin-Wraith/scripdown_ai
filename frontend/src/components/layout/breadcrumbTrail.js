// Pure breadcrumb logic: pathname + context -> crumb list. No React, no CSS,
// so it can be unit-tested with `node --test`.

export const PRODUCTION_TAB_LABELS = {
  overview: 'Overview',
  crew: 'Crew',
  cast: 'Cast',
  locations: 'Locations',
  callsheet: 'Call Sheet',
  members: 'Members',
};

export const SCRIPT_SECTION_LABELS = {
  stripboard: 'Stripboard',
  board: 'Board',
  schedule: 'Schedule',
  cast: 'Cast',
  reports: 'Reports',
  manage: 'Revisions',
};

const crumb = (label, to = null) => ({ label, to });

// Where a script lives: its production if it has one, otherwise the Scripts library.
const scriptRoot = (production) =>
  production
    ? [crumb('Productions', '/productions'), crumb(production.title || 'Production', `/productions/${production.id}`)]
    : [crumb('Scripts', '/scripts')];

/**
 * @param {{pathname: string, search?: string,
 *          script?: {id: string, title?: string}|null,
 *          production?: {id: string, title?: string}|null}} input
 * @returns {{label: string, to: string|null}[]} `to: null` marks the current page.
 */
export function buildTrail({ pathname, script = null, production = null }) {
  let m;

  if ((m = pathname.match(/^\/productions\/([^/]+)\/cast\/[^/]+$/))) {
    return [
      crumb('Productions', '/productions'),
      crumb(production?.title || 'Production', `/productions/${m[1]}`),
      crumb('Cast', `/productions/${m[1]}/cast`),
      crumb(script?.title || 'Script'),
    ];
  }

  if ((m = pathname.match(/^\/productions\/([^/]+)(?:\/([^/]+))?$/))) {
    const [, id, tab] = m;
    const title = production?.title || 'Production';
    const tabLabel = tab && tab !== 'overview' ? PRODUCTION_TAB_LABELS[tab] : null;
    return tabLabel
      ? [crumb('Productions', '/productions'), crumb(title, `/productions/${id}`), crumb(tabLabel)]
      : [crumb('Productions', '/productions'), crumb(title)];
  }

  if ((m = pathname.match(/^\/scenes\/([^/]+)$/))) {
    return [...scriptRoot(production), crumb(script?.title || 'Script')];
  }

  if ((m = pathname.match(/^\/scripts\/([^/]+)\/([^/]+)$/)) && SCRIPT_SECTION_LABELS[m[2]]) {
    return [
      ...scriptRoot(production),
      crumb(script?.title || 'Script', `/scenes/${m[1]}`),
      crumb(SCRIPT_SECTION_LABELS[m[2]]),
    ];
  }

  if (pathname === '/upload') return [crumb('Scripts', '/scripts'), crumb('Upload Script')];
  if (pathname === '/profile') return [crumb('Profile')];
  if (pathname === '/billing') return [crumb('Billing')];

  if ((m = pathname.match(/^\/series\/([^/]+)\/seasons\/[^/]+$/))) {
    return [crumb('Scripts', '/scripts'), crumb('Series', '/series'), crumb('Series', `/series/${m[1]}`), crumb('Season')];
  }
  if (/^\/series\/[^/]+$/.test(pathname)) {
    return [crumb('Scripts', '/scripts'), crumb('Series', '/series'), crumb('Series')];
  }

  if (/^\/contacts\/[^/]+/.test(pathname)) return [crumb('Contacts', '/contacts'), crumb('Contact')];
  if (/^\/locations\/[^/]+/.test(pathname)) return [crumb('Locations', '/locations'), crumb('Location')];

  return [];
}
