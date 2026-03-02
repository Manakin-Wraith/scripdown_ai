import React, { createContext, useContext, useCallback, useRef } from 'react';

/**
 * StoryDayContext — Cross-view synchronization for story day edits.
 * 
 * When any view (SceneViewer, Board, Stripboard, SceneManager) modifies story days,
 * it calls notifyStoryDayChange(). All other views that have registered a listener
 * via onStoryDayChange() will be notified to refetch their scene data.
 * 
 * This avoids prop-drilling and keeps views in sync without full-page reloads.
 */

const StoryDayContext = createContext(null);

export const StoryDayProvider = ({ children }) => {
    const listenersRef = useRef(new Set());

    const subscribe = useCallback((callback) => {
        listenersRef.current.add(callback);
        return () => listenersRef.current.delete(callback);
    }, []);

    const notifyStoryDayChange = useCallback((scriptId) => {
        listenersRef.current.forEach(cb => {
            try {
                cb(scriptId);
            } catch (e) {
                console.error('[StoryDayContext] Listener error:', e);
            }
        });
    }, []);

    return (
        <StoryDayContext.Provider value={{ subscribe, notifyStoryDayChange }}>
            {children}
        </StoryDayContext.Provider>
    );
};

/**
 * Hook to subscribe to story day changes.
 * The callback is stored in a ref so it always uses the latest version
 * without causing re-subscriptions.
 * @param {Function} callback - Called with (scriptId) when story days change
 */
export const useStoryDayListener = (callback) => {
    const ctx = useContext(StoryDayContext);
    const callbackRef = useRef(callback);
    callbackRef.current = callback;

    React.useEffect(() => {
        if (!ctx) return;
        const handler = (scriptId) => callbackRef.current(scriptId);
        return ctx.subscribe(handler);
    }, [ctx]);
};

/**
 * Hook to get the notify function for triggering story day refreshes.
 * @returns {Function} notifyStoryDayChange(scriptId)
 */
export const useStoryDayNotify = () => {
    const ctx = useContext(StoryDayContext);
    return ctx?.notifyStoryDayChange || (() => {});
};

export default StoryDayContext;
