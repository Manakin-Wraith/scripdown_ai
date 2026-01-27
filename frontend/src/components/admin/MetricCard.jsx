import PropTypes from 'prop-types';
import './MetricCard.css';

/**
 * MetricCard - Reusable card component for displaying metrics
 * 
 * @param {string} title - Card title
 * @param {string|number} value - Main metric value
 * @param {ReactNode} icon - Icon component
 * @param {string} trend - Trend or secondary info
 * @param {string} color - Color theme (blue, indigo, purple, green, yellow, red, etc.)
 * @param {function} onClick - Optional click handler to make card interactive
 * @param {string} tooltip - Optional tooltip text shown on hover
 */
export default function MetricCard({ title, value, icon, trend, color = 'blue', onClick, tooltip }) {
  const isClickable = !!onClick;
  
  return (
    <div 
      className={`metric-card metric-card--${color} ${isClickable ? 'metric-card--clickable' : ''}`}
      onClick={onClick}
      title={tooltip}
      role={isClickable ? 'button' : undefined}
      tabIndex={isClickable ? 0 : undefined}
      onKeyPress={(e) => {
        if (isClickable && (e.key === 'Enter' || e.key === ' ')) {
          onClick();
        }
      }}
    >
      <div className="metric-card__header">
        <span className="metric-card__title">{title}</span>
        <div className="metric-card__icon">
          {icon}
        </div>
      </div>
      <div className="metric-card__value">{value}</div>
      {trend && (
        <div className="metric-card__trend">{trend}</div>
      )}
    </div>
  );
}

MetricCard.propTypes = {
  title: PropTypes.string.isRequired,
  value: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
  icon: PropTypes.node.isRequired,
  trend: PropTypes.string,
  color: PropTypes.oneOf(['blue', 'indigo', 'purple', 'green', 'emerald', 'yellow', 'orange', 'red']),
  onClick: PropTypes.func,
  tooltip: PropTypes.string
};
