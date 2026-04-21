import React, { useEffect } from 'react';
import { X, CheckCircle, AlertCircle, Info } from 'lucide-react';

const Toast = ({ message, type = 'info', onClose, duration = 5000 }) => {
  useEffect(() => {
    const timer = setTimeout(onClose, duration);
    return () => clearTimeout(timer);
  }, [onClose, duration]);

  const icons = {
    success: <CheckCircle className="text-green-500" size={18} />,
    error: <AlertCircle className="text-red-500" size={18} />,
    info: <Info className="text-primary" size={18} />
  };

  const bgColors = {
    success: 'bg-green-500/10 border-green-500/20',
    error: 'bg-red-500/10 border-red-500/20',
    info: 'bg-primary/10 border-primary/20'
  };

  return (
    <div className={`fixed bottom-24 right-6 z-[300] flex items-center gap-3 p-4 rounded-xl glass-card ${bgColors[type]} border shadow-2xl animate-fade-in max-w-sm`}>
      <div className="shrink-0">
        {icons[type]}
      </div>
      <p className="text-xs font-bold text-white leading-tight">
        {message}
      </p>
      <button onClick={onClose} className="p-1 hover:bg-white/10 rounded-lg text-text-dim hover:text-white transition-all ml-2">
        <X size={14} />
      </button>
    </div>
  );
};

export default Toast;
