import './Skeleton.css';

/**
 * Skeleton — grey shimmer placeholder for initial content loads.
 * Degrades to a static block under prefers-reduced-motion (see Skeleton.css).
 * @param {{ width?: string|number, height?: string|number, radius?: string|number, className?: string, style?: object }} props
 */
export const Skeleton = ({ width = '100%', height = 16, radius, className = '', style }) => (
  <span
    className={`ui-skeleton ${className}`.trim()}
    style={{
      width,
      height,
      ...(radius != null ? { borderRadius: radius } : {}),
      ...style,
    }}
    aria-hidden="true"
  />
);

/**
 * SkeletonList — a stack of skeleton rows, for list/panel loads.
 * @param {{ count?: number, rowHeight?: string|number, className?: string, label?: string }} props
 */
export const SkeletonList = ({ count = 5, rowHeight = 40, className = '', label = 'Loading' }) => (
  <div
    className={`ui-skeleton-list ${className}`.trim()}
    role="status"
    aria-busy="true"
    aria-label={label}
  >
    {Array.from({ length: count }, (_, i) => (
      <Skeleton key={i} height={rowHeight} />
    ))}
  </div>
);

export default Skeleton;
