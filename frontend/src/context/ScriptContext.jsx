import React, { createContext, useContext, useState, useCallback } from 'react';

const ScriptContext = createContext(null);

/**
 * ScriptProvider - Caches current script metadata for breadcrumbs and navigation
 * Avoids redundant API calls when navigating between script sub-pages
 */
export const ScriptProvider = ({ children }) => {
    const [currentScript, setCurrentScript] = useState(null);

    const setScript = useCallback((script) => {
        if (script && script.id) {
            setCurrentScript({
                id: script.id,
                title: script.title || script.script_name || 'Untitled Script',
                // Add any other metadata needed for breadcrumbs
            });
        }
    }, []);

    const clearScript = useCallback(() => {
        setCurrentScript(null);
    }, []);

    return (
        <ScriptContext.Provider value={{ currentScript, setScript, clearScript }}>
            {children}
        </ScriptContext.Provider>
    );
};

export const useScript = () => {
    const context = useContext(ScriptContext);
    if (!context) {
        throw new Error('useScript must be used within a ScriptProvider');
    }
    return context;
};

export default ScriptContext;
