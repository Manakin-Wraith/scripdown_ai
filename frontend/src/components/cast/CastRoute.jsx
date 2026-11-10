// frontend/src/components/cast/CastRoute.jsx
// /scripts/:scriptId/cast — cast for a script in a production lives under the
// production's Cast tab, so send it there. Standalone scripts keep this page.
import { Navigate, useParams } from 'react-router-dom';
import { Spinner } from '../ui';
import { useScriptProduction } from '../../hooks/useScriptProduction';
import CastPage from './CastPage';

export default function CastRoute() {
    const { scriptId } = useParams();
    const { production, loading } = useScriptProduction(scriptId);

    if (loading) return <div className="production-page-loading"><Spinner size={32} /></div>;
    if (production) {
        return <Navigate to={`/productions/${production.id}/cast/${scriptId}`} replace />;
    }
    return <CastPage />;
}
