import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { ChevronRight, ArrowLeft } from 'lucide-react';
import { useScript } from '../../context/ScriptContext';
import { useScriptProduction, useProductionTitle } from '../../hooks/useScriptProduction';
import { buildTrail } from './breadcrumbTrail';
import './Breadcrumb.css';

// This component renders in the layout route, above the matched child, so
// useParams() is empty here; ids are read from the pathname instead.
const scriptIdFromPath = (pathname) => {
    const m = pathname.match(/^\/scenes\/([^/]+)$/) || pathname.match(/^\/scripts\/([^/]+)\/[^/]+$/);
    return m ? m[1] : null;
};
const productionIdFromPath = (pathname) => {
    const m = pathname.match(/^\/productions\/([^/]+)/);
    return m ? m[1] : null;
};

const Breadcrumb = () => {
    const { pathname, search } = useLocation();
    const { currentScript } = useScript();

    const scriptId = scriptIdFromPath(pathname);
    const { production: scriptProduction, scriptTitle, loading } = useScriptProduction(scriptId);
    const viewedProduction = useProductionTitle(productionIdFromPath(pathname));

    const script = scriptId
        ? { id: scriptId, title: (currentScript?.id === scriptId && currentScript.title) || scriptTitle }
        : null;

    let trail = buildTrail({
        pathname,
        search,
        script,
        production: viewedProduction || scriptProduction,
    });

    // While a script's production is still unknown, don't flash "Scripts › Script":
    // show a neutral placeholder followed by the current page only.
    if (loading && trail.length > 1) {
        trail = [{ label: '…', to: null }, trail[trail.length - 1]];
    }

    if (trail.length === 0) return null;

    const back = trail.length > 1 ? trail[trail.length - 2] : null;

    return (
        <nav className="breadcrumb-bar" aria-label="Breadcrumb">
            <ol className="breadcrumb-list desktop-only">
                {trail.map((crumb, index) => (
                    <li key={`${index}-${crumb.label}`} className="breadcrumb-item">
                        {index > 0 && <ChevronRight size={14} className="breadcrumb-separator" />}
                        {crumb.to ? (
                            <Link to={crumb.to} className="breadcrumb-link">{crumb.label}</Link>
                        ) : (
                            <span className="breadcrumb-current">{crumb.label}</span>
                        )}
                    </li>
                ))}
            </ol>

            {back?.to && (
                <Link to={back.to} className="breadcrumb-back mobile-only">
                    <ArrowLeft size={16} />
                    <span>Back to {back.label}</span>
                </Link>
            )}
        </nav>
    );
};

export default Breadcrumb;
