import './Badge.css';

/**
 * @param {{
 *  variant?: 'neutral'|'primary'|'success'|'warning'|'danger'|'info',
 *  size?: 'sm'|'md', dot?: boolean,
 *  icon?: React.ComponentType<{size?: number}>, children?: React.ReactNode
 * }} props
 */
const Badge = ({ variant = 'neutral', size = 'sm', dot = false, icon: Icon, children }) => (
  <span className={`ui-badge ui-badge--${variant} ui-badge--${size}`}>
    {dot && <span className="ui-badge-dot" />}
    {Icon && <Icon size={size === 'sm' ? 11 : 13} />}
    {children}
  </span>
);

export default Badge;
