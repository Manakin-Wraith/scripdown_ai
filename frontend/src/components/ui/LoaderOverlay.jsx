import Spinner from './Spinner';
import './LoaderOverlay.css';

/**
 * LoaderOverlay — a subtle scrim + spinner badge over a panel that already has
 * content on screen (e.g. a background refetch). The parent must be positioned
 * (position: relative). Renders nothing when `active` is false.
 * @param {{ active?: boolean, label?: string }} props
 */
const LoaderOverlay = ({ active = false, label = 'Updating…' }) => {
  if (!active) return null;
  return (
    <div className="ui-loader-overlay" role="status" aria-busy="true" aria-label={label}>
      <span className="ui-loader-overlay-badge">
        <Spinner size={15} label={label} />
        {label}
      </span>
    </div>
  );
};

export default LoaderOverlay;
