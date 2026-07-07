import { createPortal } from 'react-dom';
import { X } from 'lucide-react';
import useOverlay from './useOverlay';
import './Drawer.css';

/**
 * @param {{
 *  isOpen: boolean, onClose: () => void, title?: React.ReactNode,
 *  subtitle?: React.ReactNode, side?: 'right'|'left', width?: string,
 *  subHeader?: React.ReactNode, footer?: React.ReactNode, showClose?: boolean, children?: React.ReactNode
 * }} props
 */
const Drawer = ({
  isOpen, onClose, title, subtitle, side = 'right', width = '480px',
  subHeader, footer, showClose = true, children,
}) => {
  useOverlay({ isOpen, onClose });
  if (!isOpen) return null;

  return createPortal(
    <div className={`ui-drawer-backdrop ${side}`} onClick={onClose}>
      <div
        className={`ui-drawer ui-drawer--${side}`}
        style={{ width }}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
      >
        {(title || showClose) && (
          <div className="ui-drawer-header">
            <div className="ui-drawer-title-group">
              {title && <div className="ui-drawer-title">{title}</div>}
              {subtitle && <span className="ui-drawer-subtitle">{subtitle}</span>}
            </div>
            {showClose && (
              <button className="ui-drawer-close" onClick={onClose} aria-label="Close">
                <X size={20} />
              </button>
            )}
          </div>
        )}
        {subHeader && <div className="ui-drawer-subheader">{subHeader}</div>}
        <div className="ui-drawer-body">{children}</div>
        {footer && <div className="ui-drawer-footer">{footer}</div>}
      </div>
    </div>,
    document.body
  );
};

export default Drawer;
