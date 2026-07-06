import { useEffect } from 'react';

/**
 * Shared overlay behavior for Modal/Drawer: Escape-to-close, body
 * scroll-lock, and focus restore. Portal + focus-in is handled by the
 * consuming component (it owns the DOM node).
 * @param {{ isOpen: boolean, onClose: () => void, closeOnEscape?: boolean }} opts
 */
export default function useOverlay({ isOpen, onClose, closeOnEscape = true }) {
  useEffect(() => {
    if (!isOpen) return undefined;

    const previouslyFocused = document.activeElement;
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    const onKeyDown = (e) => {
      if (closeOnEscape && e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', onKeyDown);

    return () => {
      document.removeEventListener('keydown', onKeyDown);
      document.body.style.overflow = prevOverflow;
      if (previouslyFocused && previouslyFocused.focus) previouslyFocused.focus();
    };
  }, [isOpen, onClose, closeOnEscape]);
}
