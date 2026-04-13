import React from 'react';
import { X, Music, Image as ImageIcon } from 'lucide-react';

const MediaModal = ({ isOpen, onClose, filename, type }) => {
  if (!isOpen) return null;

  const url = `/api/downloads/${filename}?view=true`;

  return (
    <div className="fixed inset-0 z-[101] flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fade">
      <div className="glass-card w-full max-w-4xl p-0 overflow-hidden relative shadow-2xl border-primary/20">
        <div className="p-4 border-b border-border flex justify-between items-center bg-card-bg/50">
           <h3 className="text-lg font-bold text-white truncate pr-8">{filename}</h3>
           <button 
             onClick={onClose}
             className="p-1 hover:bg-white/10 rounded-full text-text-dim hover:text-white transition-all"
           >
             <X size={24} />
           </button>
        </div>

        <div className="bg-black/20 flex items-center justify-center min-h-[300px] max-h-[80vh] overflow-hidden">
          {type === 'video' && (
            <video 
              controls 
              muted
              className="w-full max-h-[70vh] outline-none"
              src={url}
            >
              Your browser does not support the video tag.
            </video>
          )}
          {type === 'audio' && (
            <div className="p-12 w-full text-center">
               <div className="mb-8 w-24 h-24 bg-primary/20 rounded-full flex items-center justify-center mx-auto text-primary animate-pulse">
                  <Music size={48} />
               </div>
               <audio 
                 controls 
                 muted
                 className="w-full max-w-md mx-auto"
                 src={url}
               >
                 Your browser does not support the audio element.
               </audio>
            </div>
          )}
          {type === 'image' && (
            <div className="relative w-full h-full flex items-center justify-center p-4">
              <img 
                src={url} 
                alt={filename}
                className="max-w-full max-h-[70vh] object-contain rounded shadow-2xl"
              />
            </div>
          )}
        </div>
        
        <div className="p-4 flex justify-between items-center bg-card-bg/30">
           <span className="text-[10px] text-text-dim font-bold uppercase tracking-widest px-4">
             {type} viewer
           </span>
           <a 
             href={`/api/downloads/${filename}`} 
             download
             className="text-xs text-primary hover:underline font-bold tracking-widest uppercase px-4"
           >
             Download Full File
           </a>
        </div>
      </div>
    </div>
  );
};

export default MediaModal;
