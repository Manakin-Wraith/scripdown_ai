import { Loader2 } from 'lucide-react';
import './Spinner.css';

/**
 * Canonical spinner. Wraps lucide Loader2 with a single keyframe.
 * @param {{ size?: number, label?: string, className?: string }} props
 */
const Spinner = ({ size = 16, label = 'Loading', className = '' }) => (
  <span className={`ui-spinner ${className}`.trim()} role="status" aria-label={label}>
    <Loader2 size={size} />
  </span>
);

export default Spinner;
