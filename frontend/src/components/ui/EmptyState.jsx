import './EmptyState.css';

/**
 * @param {{
 *  icon?: React.ComponentType<{size?: number}>, title: string,
 *  message?: React.ReactNode, action?: React.ReactNode, size?: 'sm'|'md'
 * }} props
 */
const EmptyState = ({ icon: Icon, title, message, action, size = 'md' }) => (
  <div className={`ui-empty ui-empty--${size}`}>
    {Icon && <span className="ui-empty-icon"><Icon size={size === 'sm' ? 28 : 40} /></span>}
    <span className="ui-empty-title">{title}</span>
    {message && <span className="ui-empty-message">{message}</span>}
    {action && <span className="ui-empty-action">{action}</span>}
  </div>
);

export default EmptyState;
