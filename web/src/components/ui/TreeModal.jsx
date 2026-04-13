import React, { useState, useEffect } from 'react';
import { X, Folder, ChevronRight, ChevronDown, Check } from 'lucide-react';

const TreeItem = ({ item, selected, onSelect, depth = 0 }) => {
  const [isOpen, setIsOpen] = useState(depth === 0);
  const hasChildren = item.children && item.children.length > 0;

  return (
    <div className="select-none">
      <div 
        className={`flex items-center gap-2 p-2 rounded-lg cursor-pointer transition-all ${selected === item.path ? 'bg-primary/20 text-primary border border-primary/30' : 'hover:bg-white/5 text-text-dim'}`}
        style={{ paddingLeft: `${depth * 1+1}rem` }}
        onClick={() => onSelect(item.path)}
      >
        <div 
          className="p-1 hover:bg-white/10 rounded"
          onClick={(e) => {
            if (hasChildren) {
              e.stopPropagation();
              setIsOpen(!isOpen);
            }
          }}
        >
          {hasChildren ? (
            isOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />
          ) : (
            <div className="w-[14px]" />
          )}
        </div>
        <Folder size={16} />
        <span className="text-sm font-medium truncate">{item.name || 'Root /'}</span>
        {selected === item.path && <Check size={14} className="ml-auto" />}
      </div>
      
      {hasChildren && isOpen && (
        <div className="mt-1">
          {item.children.map(child => (
            <TreeItem 
              key={child.path} 
              item={child} 
              selected={selected} 
              onSelect={onSelect} 
              depth={depth + 1} 
            />
          ))}
        </div>
      )}
    </div>
  );
};

const TreeModal = ({ isOpen, onClose, onSelect, title }) => {
  const [treeData, setTreeData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState('');

  useEffect(() => {
    if (isOpen) {
      fetchTree();
      setSelected('');
    }
  }, [isOpen]);

  const fetchTree = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/downloads/tree');
      const paths = await res.json();
      
      // Convert flat paths to nested structure
      const root = { name: '', path: '', children: [] };
      const pathMap = { '': root };
      
      paths.forEach(path => {
        if (path === '') return;
        const parts = path.split('/');
        let current = root;
        let runningPath = '';
        
        parts.forEach(part => {
          runningPath = runningPath ? `${runningPath}/${part}` : part;
          if (!pathMap[runningPath]) {
            const newNode = { name: part, path: runningPath, children: [] };
            pathMap[runningPath] = newNode;
            current.children.push(newNode);
          }
          current = pathMap[runningPath];
        });
      });
      
      setTreeData(root);
    } catch(e) {}
    setLoading(false);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[110] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade">
      <div className="glass-card w-full max-w-md flex flex-col max-h-[80vh] border-primary/20 shadow-2xl">
        <div className="p-4 border-b border-border flex justify-between items-center bg-card-bg/50">
           <h3 className="text-xl font-bold text-white">{title}</h3>
           <button onClick={onClose} className="text-text-dim hover:text-white p-2 hover:bg-white/5 rounded-lg"><X size={20}/></button>
        </div>

        <div className="flex-grow overflow-y-auto p-4 custom-scrollbar">
          {loading ? (
            <div className="flex justify-center py-12">
               <div className="animate-spin h-8 w-8 border-2 border-primary border-t-transparent rounded-full"></div>
            </div>
          ) : (
            treeData && <TreeItem item={treeData} selected={selected} onSelect={setSelected} />
          )}
        </div>

        <div className="p-4 border-t border-border flex justify-end gap-3 bg-card-bg/50">
           <button onClick={onClose} className="px-5 py-2 text-text-dim hover:text-white transition-all font-medium">Cancel</button>
           <button 
             onClick={() => onSelect(selected)}
             disabled={loading}
             className="btn-primary px-8"
           >
             Confirm Destination
           </button>
        </div>
      </div>
    </div>
  );
};

export default TreeModal;
