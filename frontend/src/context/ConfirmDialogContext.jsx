/**
 * Confirm Dialog Context - Global confirmation dialog system
 * 
 * Replaces window.confirm() with a styled modal that matches the app theme.
 * 
 * Usage:
 *   const { confirm } = useConfirmDialog();
 *   const confirmed = await confirm({
 *       title: 'Delete Script',
 *       message: 'This cannot be undone.',
 *       variant: 'danger'
 *   });
 *   if (confirmed) { // proceed }
 */

import React, { createContext, useContext, useState, useCallback } from 'react';
import { AlertTriangle, Trash2, Info, X } from 'lucide-react';
import './ConfirmDialog.css';

const ConfirmDialogContext = createContext(null);

// Variant configurations
const VARIANTS = {
    danger: {
        icon: Trash2,
        className: 'confirm-danger',
        confirmText: 'Delete'
    },
    warning: {
        icon: AlertTriangle,
        className: 'confirm-warning',
        confirmText: 'Continue'
    },
    info: {
        icon: Info,
        className: 'confirm-info',
        confirmText: 'Confirm'
    }
};

export const ConfirmDialogProvider = ({ children }) => {
    const [dialogState, setDialogState] = useState({
        isOpen: false,
        config: null,
        resolve: null
    });

    /**
     * Show confirmation dialog
     * @param {Object} options
     * @param {string} options.title - Dialog title
     * @param {string} options.message - Dialog message
     * @param {string} options.variant - 'danger' | 'warning' | 'info'
     * @param {string} options.confirmText - Custom confirm button text
     * @param {string} options.cancelText - Custom cancel button text
     * @returns {Promise<boolean>} - Resolves to true if confirmed, false if cancelled
     */
    const confirm = useCallback((options) => {
        return new Promise((resolve) => {
            setDialogState({
                isOpen: true,
                config: {
                    title: options.title || 'Confirm',
                    message: options.message || 'Are you sure?',
                    variant: options.variant || 'info',
                    confirmText: options.confirmText,
                    cancelText: options.cancelText || 'Cancel'
                },
                resolve
            });
        });
    }, []);

    const handleConfirm = useCallback(() => {
        if (dialogState.resolve) {
            dialogState.resolve(true);
        }
        setDialogState({ isOpen: false, config: null, resolve: null });
    }, [dialogState.resolve]);

    const handleCancel = useCallback(() => {
        if (dialogState.resolve) {
            dialogState.resolve(false);
        }
        setDialogState({ isOpen: false, config: null, resolve: null });
    }, [dialogState.resolve]);

    // Handle keyboard events
    const handleKeyDown = useCallback((e) => {
        if (e.key === 'Escape') {
            handleCancel();
        } else if (e.key === 'Enter') {
            handleConfirm();
        }
    }, [handleCancel, handleConfirm]);

    return (
        <ConfirmDialogContext.Provider value={{ confirm }}>
            {children}
            {dialogState.isOpen && dialogState.config && (
                <ConfirmDialog
                    config={dialogState.config}
                    onConfirm={handleConfirm}
                    onCancel={handleCancel}
                    onKeyDown={handleKeyDown}
                />
            )}
        </ConfirmDialogContext.Provider>
    );
};

/**
 * Confirm Dialog Component
 */
const ConfirmDialog = ({ config, onConfirm, onCancel, onKeyDown }) => {
    const variant = VARIANTS[config.variant] || VARIANTS.info;
    const Icon = variant.icon;
    const confirmText = config.confirmText || variant.confirmText;

    // Focus trap - focus the cancel button on mount
    React.useEffect(() => {
        const handleKeyDown = (e) => {
            if (e.key === 'Escape') {
                onCancel();
            }
        };
        
        document.addEventListener('keydown', handleKeyDown);
        return () => document.removeEventListener('keydown', handleKeyDown);
    }, [onCancel]);

    return (
        <div className="confirm-overlay" onClick={onCancel}>
            <div 
                className={`confirm-dialog ${variant.className}`}
                onClick={(e) => e.stopPropagation()}
                role="alertdialog"
                aria-modal="true"
                aria-labelledby="confirm-title"
                aria-describedby="confirm-message"
            >
                {/* Icon */}
                <div className="confirm-icon">
                    <Icon size={28} />
                </div>

                {/* Content */}
                <div className="confirm-content">
                    <h3 id="confirm-title" className="confirm-title">
                        {config.title}
                    </h3>
                    <p id="confirm-message" className="confirm-message">
                        {config.message}
                    </p>
                </div>

                {/* Actions */}
                <div className="confirm-actions">
                    <button 
                        className="confirm-btn cancel"
                        onClick={onCancel}
                    >
                        {config.cancelText}
                    </button>
                    <button 
                        className="confirm-btn primary"
                        onClick={onConfirm}
                        autoFocus
                    >
                        {confirmText}
                    </button>
                </div>
            </div>
        </div>
    );
};

/**
 * Hook to use confirm dialog
 */
export const useConfirmDialog = () => {
    const context = useContext(ConfirmDialogContext);
    if (!context) {
        throw new Error('useConfirmDialog must be used within a ConfirmDialogProvider');
    }
    return context;
};

export default ConfirmDialogContext;
