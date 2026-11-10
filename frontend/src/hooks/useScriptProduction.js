import { useEffect, useState } from 'react';
import { getScriptMetadata, getProduction } from '../services/apiService';

/**
 * Resolves the production a script belongs to (for breadcrumbs).
 * Failures resolve to `production: null`; this hook never throws.
 */
export function useScriptProduction(scriptId) {
  const [state, setState] = useState({ scriptId: null, production: null, scriptTitle: null });

  useEffect(() => {
    if (!scriptId) return undefined;
    let cancelled = false;
    getScriptMetadata(scriptId)
      .then((meta) => {
        if (cancelled) return;
        setState({
          scriptId,
          scriptTitle: meta?.title || null,
          production: meta?.production_id
            ? { id: meta.production_id, title: meta.production_title || null }
            : null,
        });
      })
      .catch(() => {
        if (!cancelled) setState({ scriptId, scriptTitle: null, production: null });
      });
    return () => { cancelled = true; };
  }, [scriptId]);

  const resolved = !!scriptId && state.scriptId === scriptId;
  return {
    production: resolved ? state.production : null,
    scriptTitle: resolved ? state.scriptTitle : null,
    loading: !!scriptId && !resolved,
  };
}

/** Resolves `{id, title}` for the production shown at /productions/:id. */
export function useProductionTitle(productionId) {
  const [state, setState] = useState({ id: null, title: null });

  useEffect(() => {
    if (!productionId) return undefined;
    let cancelled = false;
    getProduction(productionId)
      .then((data) => { if (!cancelled) setState({ id: productionId, title: data?.production?.title || null }); })
      .catch(() => { if (!cancelled) setState({ id: productionId, title: null }); });
    return () => { cancelled = true; };
  }, [productionId]);

  return state.id === productionId && productionId ? { id: productionId, title: state.title } : null;
}
