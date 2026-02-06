import { useEffect, useCallback } from 'react';

/**
 * Custom hook for keyboard shortcuts in the Interactive Viewer
 * @param {Array} extractions - List of extractions
 * @param {Object} selectedExtraction - Currently selected extraction
 * @param {Function} onSelectExtraction - Callback to select an extraction
 * @param {Function} onFocusSearch - Callback to focus search input
 * @param {Function} onCloseModal - Callback to close modal
 */
const useKeyboardShortcuts = ({
  extractions,
  selectedExtraction,
  onSelectExtraction,
  onFocusSearch,
  onCloseModal
}) => {
  const handleKeyPress = useCallback((event) => {
    // Don't trigger shortcuts if user is typing in an input
    if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') {
      // Allow Escape to blur input
      if (event.key === 'Escape') {
        event.target.blur();
      }
      return;
    }

    switch (event.key) {
      case '/':
        // Focus search input
        event.preventDefault();
        if (onFocusSearch) {
          onFocusSearch();
        }
        break;

      case 'Escape':
        // Close modal if open
        event.preventDefault();
        if (onCloseModal) {
          onCloseModal();
        }
        break;

      case 'n':
      case 'ArrowDown':
        // Next extraction
        event.preventDefault();
        if (extractions.length > 0) {
          const currentIndex = selectedExtraction 
            ? extractions.findIndex(ext => ext.id === selectedExtraction.id)
            : -1;
          const nextIndex = (currentIndex + 1) % extractions.length;
          onSelectExtraction(extractions[nextIndex]);
        }
        break;

      case 'p':
      case 'ArrowUp':
        // Previous extraction
        event.preventDefault();
        if (extractions.length > 0) {
          const currentIndex = selectedExtraction 
            ? extractions.findIndex(ext => ext.id === selectedExtraction.id)
            : 0;
          const prevIndex = currentIndex - 1 < 0 
            ? extractions.length - 1 
            : currentIndex - 1;
          onSelectExtraction(extractions[prevIndex]);
        }
        break;

      case '?':
        // Show keyboard shortcuts help (future enhancement)
        event.preventDefault();
        console.log('Keyboard shortcuts help');
        break;

      default:
        break;
    }
  }, [extractions, selectedExtraction, onSelectExtraction, onFocusSearch, onCloseModal]);

  useEffect(() => {
    document.addEventListener('keydown', handleKeyPress);

    return () => {
      document.removeEventListener('keydown', handleKeyPress);
    };
  }, [handleKeyPress]);

  return null;
};

export default useKeyboardShortcuts;
