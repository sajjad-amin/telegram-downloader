import React, { useState } from 'react';
import { Link2, Play, Pause, Square, X } from 'lucide-react';
import Modal from './ui/Modal';

const SingleDownload = ({ activeProfile, tasks, onRemoveTask }) => {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [modal, setModal] = useState({ open: false, title: '', message: '', onConfirm: null });

  const showAlert = (title, message) => {
    setModal({ open: true, title, message, type: 'alert', onConfirm: () => setModal({ open: false }) });
  };

  const handleDownload = async () => {
    if (!url) return;
    if (!activeProfile) {
      showAlert("Profile Required", "Please select a valid profile/account first!");
      return;
    }
    setLoading(true);
    try {
      const res = await fetch('/api/download/single', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url, profile: activeProfile })
      });
      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.error || 'Failed to start download');
      }
      setUrl('');
    } catch(e) {
      showAlert("Download Error", e.message);
    }
    setLoading(false);
  };

  const handleControl = async (action, taskId) => {
    try {
      await fetch(`/api/download/${action}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task_id: taskId })
      });
    } catch(e) {}
  };

  const activeTasks = Object.entries(tasks)
    .filter(([id, task]) => {
        const isSingle = id.startsWith('single');
        const matchesProfile = !task.profile || task.profile === activeProfile;
        // Keep in list even if finished, Dashboard will clear the state after 5s
        return isSingle && matchesProfile;
    })
    .reverse();

  return (
    <div className="space-y-6">
      <Modal 
        isOpen={modal.open} 
        title={modal.title} 
        message={modal.message} 
        type={modal.type}
        onConfirm={modal.onConfirm}
        onCancel={() => setModal({ ...modal, open: false })}
      />

      <div className="space-y-3">
        <h2 className="text-sm font-bold flex items-center gap-2 text-white">
          <Link2 size={16} className="text-primary" /> Single Media Download
        </h2>
        <div className="flex gap-2">
          <input 
            type="text" 
            placeholder="Paste Telegram link here..."
            className="input-field"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />
          <button 
            onClick={handleDownload}
            disabled={loading}
            className="btn-primary flex items-center gap-2 whitespace-nowrap min-w-[100px]"
          >
            {loading ? <div className="animate-spin h-3 w-3 border-t-2 border-white rounded-full"></div> : <Play size={14} fill="currentColor" />}
            Start
          </button>
        </div>
      </div>

      <div className="space-y-3">
        <h3 className="text-[10px] font-bold text-text-dim uppercase tracking-widest flex justify-between items-center px-1">
          Active Downloads
          {activeTasks.length > 0 && (
            <span className="text-primary">{activeTasks.length} running</span>
          )}
        </h3>
        <div className="space-y-2">
          {activeTasks.length === 0 && (
            <div className="py-8 border border-dashed border-border rounded-lg text-center">
               <p className="text-text-dim text-xs italic">No active downloads</p>
            </div>
          )}
          {activeTasks.map(([id, task]) => (
            <div key={id} className="p-3 bg-[#0d0e12] border border-border rounded flex flex-col gap-2 animate-fade">
              <div className="flex justify-between items-start">
                <div className="flex-grow min-w-0 pr-2">
                   <p className="text-xs font-medium truncate text-white">{task.text}</p>
                </div>
                 <div className="flex gap-1.5 flex-shrink-0">
                    {['done', 'failed', 'cancelled'].includes(task.status) ? (
                      <button onClick={() => onRemoveTask && onRemoveTask(id)} className="p-1.5 hover:text-white rounded transition-all text-text-dim" title="Dismiss"><X size={14} /></button>
                    ) : (
                      <>
                        {task.status === 'paused' ? (
                          <button onClick={() => handleControl('resume', id)} className="p-1.5 hover:text-green-500 rounded transition-all"><Play size={14} fill="currentColor" /></button>
                        ) : (
                          <button onClick={() => handleControl('pause', id)} className="p-1.5 hover:text-yellow-500 rounded transition-all"><Pause size={14} fill="currentColor" /></button>
                        )}
                        <button onClick={() => handleControl('cancel', id)} className="p-1.5 hover:text-red-500 rounded transition-all"><Square size={14} fill="currentColor" /></button>
                      </>
                    )}
                 </div>
              </div>
              
              <div className="space-y-1">
                <div className="h-1 bg-bg-dark rounded-full overflow-hidden">
                  <div className={`h-full transition-all duration-300 ${task.status === 'paused' ? 'bg-yellow-500' : 'bg-primary'}`} style={{ width: `${task.progress}%` }}></div>
                </div>
                <div className="flex justify-between text-[10px] font-bold text-text-dim uppercase">
                   <span>{task.status}</span>
                   <span>{Math.round(task.progress)}%</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default SingleDownload;
