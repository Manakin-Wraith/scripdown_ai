import { useState, useEffect, useRef, useCallback } from 'react';

/**
 * Custom hook for virtual scrolling large text content
 * @param {string} content - Full text content
 * @param {number} itemHeight - Height of each line in pixels
 * @param {number} containerHeight - Height of visible container
 * @param {number} overscan - Number of extra items to render above/below viewport
 */
const useVirtualScroll = (content, itemHeight = 20, containerHeight = 600, overscan = 10) => {
  const [scrollTop, setScrollTop] = useState(0);
  const containerRef = useRef(null);

  const lines = content.split('\n');
  const totalHeight = lines.length * itemHeight;

  const startIndex = Math.max(0, Math.floor(scrollTop / itemHeight) - overscan);
  const endIndex = Math.min(
    lines.length,
    Math.ceil((scrollTop + containerHeight) / itemHeight) + overscan
  );

  const visibleLines = lines.slice(startIndex, endIndex);
  const offsetY = startIndex * itemHeight;

  const handleScroll = useCallback((event) => {
    setScrollTop(event.target.scrollTop);
  }, []);

  useEffect(() => {
    const container = containerRef.current;
    if (container) {
      container.addEventListener('scroll', handleScroll);
      return () => container.removeEventListener('scroll', handleScroll);
    }
  }, [handleScroll]);

  return {
    containerRef,
    visibleLines,
    offsetY,
    totalHeight,
    startIndex,
    endIndex
  };
};

export default useVirtualScroll;
