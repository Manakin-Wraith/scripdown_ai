import React from 'react';
import { Link, useLocation, useParams } from 'react-router-dom';
import { ChevronRight, ArrowLeft } from 'lucide-react';
import { useScript } from '../../context/ScriptContext';
import './Breadcrumb.css';

/**
 * Route configuration for breadcrumbs
 * Maps route patterns to their display labels
 */
const ROUTE_CONFIG = {
    '/scripts': { label: 'My Scripts', parent: null },
    '/scenes/:scriptId': { label: 'Scene Breakdown', parent: '/scripts' },
    '/scripts/:scriptId/edit': { label: 'Edit Scenes', parent: '/scripts' },
    '/scripts/:scriptId/manage': { label: 'Scene Manager', parent: '/scripts' },
    '/scripts/:scriptId/reports': { label: 'Reports', parent: '/scripts' },
    '/scripts/:scriptId/stripboard': { label: 'Stripboard', parent: '/scripts' },
    '/scripts/:scriptId/characters/:characterName': { label: 'Character', parent: '/scripts' },
    '/upload': { label: 'Upload Script', parent: '/scripts' },
};

/**
 * Match current path to route config
 */
const matchRoute = (pathname) => {
    for (const [pattern, config] of Object.entries(ROUTE_CONFIG)) {
        const regex = new RegExp(
            '^' + pattern.replace(/:[^/]+/g, '[^/]+') + '$'
        );
        if (regex.test(pathname)) {
            return { pattern, ...config };
        }
    }
    return null;
};

const Breadcrumb = () => {
    const location = useLocation();
    const params = useParams();
    const { currentScript } = useScript();
    
    const routeConfig = matchRoute(location.pathname);
    
    // Don't show breadcrumb on root pages
    if (!routeConfig || location.pathname === '/scripts') {
        return null;
    }

    // Build breadcrumb trail
    const crumbs = [];
    
    // Always start with "My Scripts"
    crumbs.push({
        label: 'My Scripts',
        path: '/scripts',
        isLink: true
    });

    // Add script name if we have a scriptId in the route
    const scriptId = params.scriptId;
    const isSceneBreakdown = location.pathname === `/scenes/${scriptId}`;
    
    if (scriptId && !isSceneBreakdown) {
        // Only add script link if we're NOT on the scene breakdown page itself
        const scriptTitle = currentScript?.title || 'Script';
        crumbs.push({
            label: scriptTitle,
            path: `/scenes/${scriptId}`,
            isLink: true
        });
    }

    // Add current page (not a link)
    crumbs.push({
        label: isSceneBreakdown ? (currentScript?.title || routeConfig.label) : routeConfig.label,
        path: location.pathname,
        isLink: false
    });

    // Mobile: Show simplified back navigation
    const backPath = scriptId ? `/scenes/${scriptId}` : '/scripts';
    const backLabel = scriptId ? (currentScript?.title || 'Script') : 'My Scripts';

    return (
        <nav className="breadcrumb-bar" aria-label="Breadcrumb">
            {/* Desktop breadcrumbs */}
            <ol className="breadcrumb-list desktop-only">
                {crumbs.map((crumb, index) => (
                    <li key={crumb.path} className="breadcrumb-item">
                        {index > 0 && (
                            <ChevronRight size={14} className="breadcrumb-separator" />
                        )}
                        {crumb.isLink ? (
                            <Link to={crumb.path} className="breadcrumb-link">
                                {crumb.label}
                            </Link>
                        ) : (
                            <span className="breadcrumb-current">{crumb.label}</span>
                        )}
                    </li>
                ))}
            </ol>

            {/* Mobile back link */}
            <Link to={backPath} className="breadcrumb-back mobile-only">
                <ArrowLeft size={16} />
                <span>Back to {backLabel}</span>
            </Link>
        </nav>
    );
};

export default Breadcrumb;
