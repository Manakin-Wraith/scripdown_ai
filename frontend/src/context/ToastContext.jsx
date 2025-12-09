/**
 * Toast Context - Global toast notification system
 * 
 * Provides:
 * - Show success, error, info, warning toasts
 * - Auto-dismiss with configurable duration
 * - Action buttons on toasts
 * - Queue management for multiple toasts
 */

import React, { createContext, useContext, useState, useCallback } from 'react';
import { CheckCircle, AlertCircle, Info, AlertTriangle, X } from 'lucide-react';
import './Toast.css';

const ToastContext = createContext(null);

// Toast types with their icons and colors
const TOAST_TYPES = {
    success: {
        icon: CheckCircle,
        className: 'toast-success'
    },
    error: {
        icon: AlertCircle,
        className: 'toast-error'
    },
    info: {
        icon: Info,
        className: 'toast-info'
    },
    warning: {
        icon: AlertTriangle,
        className: 'toast-warning'
    }
};

// Default auto-dismiss duration (ms)
const DEFAULT_DURATION = 5000;

let toastId = 0;

export const ToastProvider = ({ children }) => {
    const [toasts, setToasts] = useState([]);

    /**
     * Add a new toast
     * @param {Object} options - Toast options
     * @param {string} options.type - 'success' | 'error' | 'info' | 'warning'
     * @param {string} options.title - Toast title
     * @param {string} options.message - Toast message
     * @param {number} options.duration - Auto-dismiss duration (0 = no auto-dismiss)
     * @param {Object} options.action - { label: string, onClick: function }
     */
    const addToast = useCallback((options) => {
        const id = ++toastId;
        const toast = {
            id,
            type: options.type || 'info',
            title: options.title,
            message: options.message,
            duration: options.duration ?? DEFAULT_DURATION,
            action: options.action
        };

        setToasts(prev => [...prev, toast]);

        // Auto-dismiss
        if (toast.duration > 0) {
            setTimeout(() => {
                removeToast(id);
            }, toast.duration);
        }

        return id;
    }, []);

    /**
     * Remove a toast by ID
     */
    const removeToast = useCallback((id) => {
        setToasts(prev => prev.filter(t => t.id !== id));
    }, []);

    /**
     * Convenience methods
     */
    const success = useCallback((title, message, options = {}) => {
        return addToast({ type: 'success', title, message, ...options });
    }, [addToast]);

    const error = useCallback((title, message, options = {}) => {
        return addToast({ type: 'error', title, message, ...options });
    }, [addToast]);

    const info = useCallback((title, message, options = {}) => {
        return addToast({ type: 'info', title, message, ...options });
    }, [addToast]);

    const warning = useCallback((title, message, options = {}) => {
        return addToast({ type: 'warning', title, message, ...options });
    }, [addToast]);

    const value = {
        toasts,
        addToast,
        removeToast,
        success,
        error,
        info,
        warning
    };

    return (
        <ToastContext.Provider value={value}>
            {children}
            <ToastContainer toasts={toasts} onDismiss={removeToast} />
        </ToastContext.Provider>
    );
};

/**
 * Toast Container - renders all active toasts
 */
const ToastContainer = ({ toasts, onDismiss }) => {
    if (toasts.length === 0) return null;

    return (
        <div className="toast-container">
            {toasts.map(toast => (
                <Toast key={toast.id} toast={toast} onDismiss={onDismiss} />
            ))}
        </div>
    );
};

/**
 * Individual Toast component
 */
const Toast = ({ toast, onDismiss }) => {
    const config = TOAST_TYPES[toast.type] || TOAST_TYPES.info;
    const Icon = config.icon;

    return (
        <div className={`toast ${config.className}`}>
            <div className="toast-icon">
                <Icon size={20} />
            </div>
            <div className="toast-content">
                {toast.title && <div className="toast-title">{toast.title}</div>}
                {toast.message && <div className="toast-message">{toast.message}</div>}
                {toast.action && (
                    <button 
                        className="toast-action"
                        onClick={() => {
                            toast.action.onClick();
                            onDismiss(toast.id);
                        }}
                    >
                        {toast.action.label}
                    </button>
                )}
            </div>
            <button 
                className="toast-dismiss"
                onClick={() => onDismiss(toast.id)}
            >
                <X size={16} />
            </button>
        </div>
    );
};

/**
 * Hook to use toast context
 */
export const useToast = () => {
    const context = useContext(ToastContext);
    if (!context) {
        throw new Error('useToast must be used within a ToastProvider');
    }
    return context;
};

export default ToastContext;
