import { useEffect, useState } from 'react';
import { getScriptMetadata, getProduction } from '../services/apiService';

const EMPTY_SCRIPT_STATE = { scriptId: null, production: null, scriptTitle: null };
const PRODUCTION_UPDATED = 'slateone:production-updated';

/** Call after a production is saved so open breadcrumbs pick up the new title. */
export const announceProductionUpdated = (production) => {
  if (production?.id) window.dispatchEvent(new CustomEvent(PRODUCTION_UPDATED, { detail: production }));
};

/**
 * Resolves the production a script belongs to (for breadcrumbs).
 * Failures resolve to `production: null`; this hook never throws.
 */
export function useScriptProduction(scriptId) {
  const [state, setState] = useState(EMPTY_SCRIPT_STATE);

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
    // Clear on every change of script (including leaving script pages), so a
    // revisit never shows the previous visit's production while refetching.
    return () => { cancelled = true; setState(EMPTY_SCRIPT_STATE); };
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
    const onUpdated = (e) => {
      if (e.detail?.id === productionId) setState({ id: productionId, title: e.detail.title || null });
    };
    window.addEventListener(PRODUCTION_UPDATED, onUpdated);
    return () => { cancelled = true; window.removeEventListener(PRODUCTION_UPDATED, onUpdated); };
  }, [productionId]);

  return state.id === productionId && productionId ? { id: productionId, title: state.title } : null;
}
