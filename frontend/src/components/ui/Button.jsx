import Spinner from './Spinner';
import './Button.css';

/**
 * @param {{
 *  variant?: 'primary'|'secondary'|'danger'|'ghost',
 *  size?: 'sm'|'md', loading?: boolean, disabled?: boolean,
 *  icon?: React.ComponentType<{size?: number}>, iconPosition?: 'left'|'right',
 *  fullWidth?: boolean, children?: React.ReactNode, className?: string
 * }} props
 */
const Button = ({
  variant = 'primary', size = 'md', loading = false, disabled = false,
  icon: Icon, iconPosition = 'left', fullWidth = false,
  children, className = '', ...rest
}) => {
  const iconSize = size === 'sm' ? 14 : 16;
  const cls = [
    'ui-btn', `ui-btn--${variant}`, `ui-btn--${size}`,
    fullWidth ? 'ui-btn--full' : '', className,
  ].filter(Boolean).join(' ');

  return (
    <button className={cls} disabled={disabled || loading} {...rest}>
      {loading && <Spinner size={iconSize} />}
      {!loading && Icon && iconPosition === 'left' && <Icon size={iconSize} />}
      {children}
      {!loading && Icon && iconPosition === 'right' && <Icon size={iconSize} />}
    </button>
  );
};

export default Button;
