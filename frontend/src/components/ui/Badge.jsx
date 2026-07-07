import './Badge.css';

/**
 * @param {{
 *  variant?: 'neutral'|'primary'|'success'|'warning'|'danger'|'info',
 *  size?: 'sm'|'md', dot?: boolean,
 *  icon?: React.ComponentType<{size?: number}>, className?: string,
 *  children?: React.ReactNode
 * }} props
 * Extra props (title, aria-*, onClick, …) are forwarded onto the span.
 */
const Badge = ({ variant = 'neutral', size = 'sm', dot = false, icon: Icon, className = '', children, ...rest }) => (
  <span
    className={`ui-badge ui-badge--${variant} ui-badge--${size}${className ? ` ${className}` : ''}`}
    {...rest}
  >
    {dot && <span className="ui-badge-dot" />}
    {Icon && <Icon size={size === 'sm' ? 11 : 13} />}
    {children}
  </span>
);

export default Badge;
