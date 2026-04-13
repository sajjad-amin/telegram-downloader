import React from 'react';
import { X, AlertCircle } from 'lucide-react';

const Modal = ({ isOpen, title, message, onConfirm, onCancel, type = 'confirm' }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade">
      <div className="glass-card w-full max-w-md p-6 overflow-hidden relative">
        <button 
          onClick={onCancel}
          className="absolute top-4 right-4 text-text-dim hover:text-white transition-colors"
        >
          <X size={20} />
        </button>

        <div className="flex items-center gap-4 mb-4">
          <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center text-primary">
            <AlertCircle size={24} />
          </div>
          <h3 className="text-xl font-bold text-white">{title}</h3>
        </div>

        <p className="text-text-dim mb-8 leading-relaxed">
          {message}
        </p>

        <div className="flex justify-end gap-3">
          {type === 'confirm' && (
            <button 
              onClick={onCancel}
              className="px-6 py-2 rounded-lg border border-border text-text-dim hover:text-white transition-all font-medium"
            >
              Cancel
            </button>
          )}
          <button 
            onClick={onConfirm}
            className="btn-primary px-8"
          >
            {type === 'confirm' ? 'Confirm' : 'OK'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default Modal;
