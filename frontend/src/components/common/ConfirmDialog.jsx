import React from 'react';
import { AlertCircle, CheckCircle, Info, X } from 'lucide-react';
import './ConfirmDialog.css';

const ConfirmDialog = ({ 
    isOpen, 
    onClose, 
    onConfirm, 
    title, 
    message, 
    confirmText = 'OK',
    cancelText = 'Cancel',
    type = 'confirm', // 'confirm', 'alert', 'success', 'error'
    confirmButtonClass = 'btn-primary'
}) => {
    if (!isOpen) return null;

    const handleConfirm = () => {
        onConfirm();
        onClose();
    };

    const handleCancel = () => {
        onClose();
    };

    const getIcon = () => {
        switch (type) {
            case 'success':
                return <CheckCircle size={24} className="icon-success" />;
            case 'error':
                return <AlertCircle size={24} className="icon-error" />;
            case 'alert':
                return <Info size={24} className="icon-info" />;
            default:
                return <AlertCircle size={24} className="icon-warning" />;
        }
    };

    return (
        <div className="confirm-dialog-overlay" onClick={handleCancel}>
            <div className="confirm-dialog" onClick={(e) => e.stopPropagation()}>
                <button className="dialog-close" onClick={handleCancel}>
                    <X size={20} />
                </button>

                <div className="dialog-header">
                    {getIcon()}
                    <h3>{title}</h3>
                </div>

                <div className="dialog-body">
                    <p>{message}</p>
                </div>

                <div className="dialog-footer">
                    {type === 'confirm' && (
                        <button 
                            className="btn-secondary"
                            onClick={handleCancel}
                        >
                            {cancelText}
                        </button>
                    )}
                    <button 
                        className={confirmButtonClass}
                        onClick={handleConfirm}
                    >
                        {confirmText}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default ConfirmDialog;
