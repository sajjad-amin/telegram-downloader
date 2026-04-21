import React from 'react';
import { X, AlertCircle } from 'lucide-react';

const Modal = ({ isOpen, title, message, onConfirm, onCancel, type = 'confirm', children, danger = false }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[200] flex items-center justify-center p-4 bg-black/70 backdrop-blur-md animate-fade">
      <div className="glass-card w-full max-w-md p-6 relative overflow-y-auto max-h-[90vh] shadow-3xl border-primary/20">
        <button 
          onClick={onCancel}
          className="absolute top-4 right-4 text-text-dim hover:text-white transition-colors"
        >
          <X size={20} />
        </button>

        <div className="flex items-center gap-4 mb-4">
          <div className={`w-12 h-12 rounded-full flex items-center justify-center ${danger ? 'bg-red-500/10 text-red-500' : 'bg-primary/10 text-primary'}`}>
            <AlertCircle size={24} />
          </div>
          <h3 className="text-xl font-bold text-white">{title}</h3>
        </div>

        <p className="text-text-dim leading-relaxed">
          {message}
        </p>

        {children}

        <div className="flex justify-end gap-3 mt-8">
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
            className={`${danger ? 'bg-red-600 hover:bg-red-500' : 'btn-primary'} px-8 py-2 rounded-lg font-bold text-white transition-all`}
          >
            {type === 'confirm' ? 'Confirm' : 'OK'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default Modal;
