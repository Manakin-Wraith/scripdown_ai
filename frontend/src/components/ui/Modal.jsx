import { createPortal } from 'react-dom';
import { X } from 'lucide-react';
import useOverlay from './useOverlay';
import './Modal.css';

/**
 * @param {{
 *  isOpen: boolean, onClose: () => void, title?: React.ReactNode,
 *  size?: 'sm'|'md'|'lg', footer?: React.ReactNode, showClose?: boolean,
 *  closeOnOverlay?: boolean, closeOnEscape?: boolean, children?: React.ReactNode
 * }} props
 */
const Modal = ({
  isOpen, onClose, title, size = 'md', footer,
  showClose = true, closeOnOverlay = true, closeOnEscape = true, children,
}) => {
  useOverlay({ isOpen, onClose, closeOnEscape });
  if (!isOpen) return null;

  return createPortal(
    <div
      className="ui-modal-overlay"
      onClick={closeOnOverlay ? onClose : undefined}
    >
      <div
        className={`ui-modal ui-modal--${size}`}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
      >
        {(title || showClose) && (
          <div className="ui-modal-header">
            <span className="ui-modal-title">{title}</span>
            {showClose && (
              <button className="ui-modal-close" onClick={onClose} aria-label="Close">
                <X size={20} />
              </button>
            )}
          </div>
        )}
        <div className="ui-modal-body">{children}</div>
        {footer && <div className="ui-modal-footer">{footer}</div>}
      </div>
    </div>,
    document.body
  );
};

export default Modal;
