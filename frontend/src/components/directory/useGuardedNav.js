import { useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useConfirmDialog } from '../../context/ConfirmDialogContext';

/**
 * Shared "discard unsaved changes?" guard for the directory pages. The detail
 * pane reports its dirty state through `setPaneDirty`; `guardedNav` prompts
 * before navigating away while the pane is dirty.
 */
export default function useGuardedNav() {
    const navigate = useNavigate();
    const { confirm } = useConfirmDialog();
    const dirtyRef = useRef(false);

    const setPaneDirty = useCallback((v) => { dirtyRef.current = Boolean(v); }, []);

    const guardedNav = useCallback(async (to) => {
        if (dirtyRef.current) {
            const ok = await confirm({
                title: 'Discard unsaved changes?',
                message: 'You have unsaved changes in the form. Leaving now will lose them.',
                variant: 'warning',
                confirmText: 'Discard',
                cancelText: 'Keep editing',
            });
            if (!ok) return;
            dirtyRef.current = false;
        }
        navigate(to);
    }, [confirm, navigate]);

    return { setPaneDirty, guardedNav };
}
