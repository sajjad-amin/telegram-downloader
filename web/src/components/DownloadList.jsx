import React, { useState, useEffect, useRef, useMemo } from 'react';
import { File, Download, Trash2, RefreshCw, Eye, Film, Music, Image as ImageIcon, Folder, FolderPlus, Move, Copy, ChevronLeft, ChevronRight, MoreVertical, ArrowUpDown, CheckSquare, Square, Check, X } from 'lucide-react';
import Modal from './ui/Modal';
import MediaModal from './ui/MediaModal';
import TreeModal from './ui/TreeModal';

const DownloadList = () => {
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [currentPath, setCurrentPath] = useState('');
  const [activeMenu, setActiveMenu] = useState(null);

  const [selectedPaths, setSelectedPaths] = useState([]);
  const [sortBy, setSortBy] = useState('date');
  const [sortOrder, setSortOrder] = useState('desc');

  const [deleteModal, setDeleteModal] = useState({ open: false, type: 'single', paths: [] });
  const [viewModal, setViewModal] = useState({ open: false, filename: '', type: '', path: '' });
  const [treeModal, setTreeModal] = useState({ open: false, action: '', src: '' });
  const [mkdirModal, setMkdirModal] = useState({ open: false, name: '' });

  const menuRef = useRef(null);

  const fetchFiles = async () => {
    setLoading(true);
    try {
      const res = await fetch(`/api/downloads?path=${encodeURIComponent(currentPath)}`);
      const data = await res.json();
      setFiles(data);
      setSelectedPaths([]);
    } catch (e) { }
    setLoading(false);
  };

  useEffect(() => {
    fetchFiles();
  }, [currentPath]);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (menuRef.current && !menuRef.current.contains(event.target)) setActiveMenu(null);
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const formatDate = (dateStr) => {
    if (!dateStr) return '--';
    // Handle both 'YYYY-MM-DD HH:MM:SS' and ISO formats
    const date = new Date(dateStr.includes('T') ? dateStr : dateStr.replace(' ', 'T'));
    
    return date.toLocaleString('en-GB', {
      timeZone: 'Asia/Dhaka',
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true
    }).replace(',', ' •');
  };

  const sortedFiles = useMemo(() => {
    const sorted = [...files].sort((a, b) => {
      if (a.is_dir && !b.is_dir) return -1;
      if (!a.is_dir && b.is_dir) return 1;
      let valA = a[sortBy];
      let valB = b[sortBy];
      if (sortBy === 'name') {
        valA = valA.toLowerCase();
        valB = valB.toLowerCase();
      }
      if (valA < valB) return sortOrder === 'asc' ? -1 : 1;
      if (valA > valB) return sortOrder === 'asc' ? 1 : -1;
      return 0;
    });
    return sorted;
  }, [files, sortBy, sortOrder]);

  const toggleSelect = (path) => {
    setSelectedPaths(prev =>
      prev.includes(path) ? prev.filter(p => p !== path) : [...prev, path]
    );
  };

  const toggleSelectAll = () => {
    if (selectedPaths.length === sortedFiles.length && sortedFiles.length > 0) {
      setSelectedPaths([]);
    } else {
      setSelectedPaths(sortedFiles.map(f => f.path));
    }
  };

  const handleAction = async (dst) => {
    const { action, src } = treeModal;
    try {
      await fetch(`/api/downloads/${action}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ src, dst })
      });
      setTreeModal({ open: false, action: '', src: '' });
      fetchFiles();
    } catch (e) { }
  };

  const handleView = (item) => {
    const ext = item.name.split('.').pop().toLowerCase();
    let type = 'image';
    if (['mp4', 'webm', 'mov', 'mkv'].includes(ext)) type = 'video';
    else if (['mp3', 'wav', 'ogg', 'm4a'].includes(ext)) type = 'audio';
    setViewModal({ open: true, filename: item.name, type, path: item.path });
  };

  const formatSize = (bytes) => {
    if (!bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const getFileIcon = (item) => {
    if (item.is_dir) return <Folder size={18} className="text-primary" />;
    const ext = item.name.split('.').pop().toLowerCase();
    if (['mp4', 'mkv', 'webm', 'mov'].includes(ext)) return <Film size={18} className="text-primary" />;
    if (['mp3', 'wav', 'ogg', 'm4a'].includes(ext)) return <Music size={18} className="text-primary" />;
    if (['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(ext)) return <ImageIcon size={18} className="text-primary" />;
    return <File size={18} className="text-primary" />;
  };

  const isViewable = (item) => {
    if (item.is_dir) return false;
    const ext = item.name.split('.').pop().toLowerCase();
    return ['mp4', 'webm', 'mp3', 'wav', 'jpg', 'jpeg', 'png', 'gif', 'webp', 'mov'].includes(ext);
  };

  const breadcrumbs = currentPath.split('/').filter(p => p);

  const toggleSort = (col) => {
    if (sortBy === col) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(col);
      setSortOrder('asc');
    }
  };

  return (
    <div className="space-y-6">
      <Modal
        isOpen={deleteModal.open}
        title="Confirm Deletion"
        message={deleteModal.type === 'bulk' ? `Remove ${deleteModal.paths.length} items permanently?` : `Delete "${deleteModal.paths[0]?.split('/').pop()}"?`}
        onConfirm={async () => {
          const paths = deleteModal.paths;
          setDeleteModal({ open: false, type: 'single', paths: [] });
          if (deleteModal.type === 'bulk') {
            await fetch('/api/downloads/delete-bulk', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ paths }) });
          } else {
            await fetch(`/api/downloads/${encodeURIComponent(paths[0])}`, { method: 'DELETE' });
          }
          fetchFiles();
        }}
        onCancel={() => setDeleteModal({ open: false, type: 'single', paths: [] })}
        danger={true}
      />

      <MediaModal isOpen={viewModal.open} onClose={() => setViewModal({ open: false, filename: '', type: '', path: '' })} filename={viewModal.path} type={viewModal.type} />
      <TreeModal isOpen={treeModal.open} title={`${treeModal.action === 'move' ? 'Move' : 'Copy'} to...`} onSelect={handleAction} onClose={() => setTreeModal({ open: false, action: '', src: '' })} />

      {mkdirModal.open && (
        <div className="fixed inset-0 z-[130] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="glass-card w-full max-w-sm p-6">
            <h3 className="text-xl font-bold text-white mb-4">New Folder</h3>
            <input autoFocus className="input-field mb-6" value={mkdirModal.name} onChange={(e) => setMkdirModal({ ...mkdirModal, name: e.target.value })} onKeyDown={(e) => e.key === 'Enter' && setMkdirModal({ ...mkdirModal, trigger: true })} />
            <div className="flex justify-end gap-3 font-bold uppercase text-[11px] tracking-widest">
              <button onClick={() => setMkdirModal({ open: false, name: '' })} className="px-4 py-2 text-text-dim">Cancel</button>
              <button onClick={async () => {
                await fetch('/api/downloads/mkdir', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ parent: currentPath, name: mkdirModal.name }) });
                setMkdirModal({ open: false, name: '' });
                fetchFiles();
              }} className="btn-primary">Create</button>
            </div>
          </div>
        </div>
      )}

      {/* Action Menu Backdrop/Sheet */}
      {activeMenu && (
        <>
          <div className="fixed inset-0 z-[110] bg-black/40 backdrop-blur-[2px]" onClick={() => setActiveMenu(null)} />
          <div ref={menuRef} className="fixed bottom-0 left-0 right-0 z-[120] md:absolute md:bottom-auto md:left-auto md:right-0 md:mt-2 md:w-64 glass-card bg-[#16181d] shadow-3xl animate-fade rounded-t-3xl md:rounded-2xl pb-10 md:pb-3 pt-2">
            <div className="w-12 h-1 bg-white/10 rounded-full mx-auto mb-4 mt-1 md:hidden" />
            <div className="px-6 py-2 mb-2 flex justify-between items-center md:hidden">
              <span className="text-sm font-bold text-white truncate max-w-[200px]">{activeMenu.name}</span>
              <button onClick={() => setActiveMenu(null)} className="p-1.5 bg-white/5 rounded-full"><X size={18} /></button>
            </div>

            {activeMenu.is_dir ? (
              <button onClick={() => { setCurrentPath(activeMenu.path); setActiveMenu(null); }} className="w-full flex items-center gap-4 px-6 md:px-5 py-4 md:py-3 text-sm md:text-[11px] font-black uppercase text-text-dim hover:text-white hover:bg-white/5 transition-all">
                <Folder size={18} className="text-primary" /> Open Folder
              </button>
            ) : (
              <a href={`/api/downloads/${activeMenu.path}`} download className="flex items-center gap-4 px-6 md:px-5 py-4 md:py-3 text-sm md:text-[11px] font-black uppercase text-text-dim hover:text-white hover:bg-white/5 transition-all">
                <Download size={18} className="text-primary" /> Download
              </a>
            )}

            <button onClick={() => { setTreeModal({ open: true, action: 'move', src: activeMenu.path }); setActiveMenu(null); }} className="w-full flex items-center gap-4 px-6 md:px-5 py-4 md:py-3 text-sm md:text-[11px] font-black uppercase text-text-dim hover:text-white hover:bg-white/5 transition-all">
              <Move size={18} className="text-primary" /> Move Item
            </button>
            <button onClick={() => { setTreeModal({ open: true, action: 'copy', src: activeMenu.path }); setActiveMenu(null); }} className="w-full flex items-center gap-4 px-6 md:px-5 py-4 md:py-3 text-sm md:text-[11px] font-black uppercase text-text-dim hover:text-white hover:bg-white/5 transition-all">
              <Copy size={18} className="text-primary" /> Duplicate
            </button>
            <div className="h-px bg-white/5 my-2 mx-6 md:mx-4" />
            <button onClick={() => { setDeleteModal({ open: true, type: 'single', paths: [activeMenu.path] }); setActiveMenu(null); }} className="w-full flex items-center gap-4 px-6 md:px-5 py-4 md:py-3 text-sm md:text-[11px] font-black uppercase text-red-500 hover:bg-red-500/10 transition-all">
              <Trash2 size={18} /> Delete Permanently
            </button>
          </div>
        </>
      )}

      {/* Header Bars */}
      <div className="flex justify-between items-center gap-4 px-1">
        <div className="flex items-center gap-1.5 text-[11px] md:text-sm font-black uppercase tracking-widest text-text-dim overflow-hidden">
          <button onClick={() => setCurrentPath('')} className="hover:text-primary">ROOT</button>
          {breadcrumbs.map((crumb, idx) => (
            <React.Fragment key={idx}>
              <ChevronRight size={14} className="opacity-40" />
              <button onClick={() => setCurrentPath(breadcrumbs.slice(0, idx + 1).join('/'))} className="hover:text-primary truncate max-w-[100px]">{crumb.toUpperCase()}</button>
            </React.Fragment>
          ))}
        </div>
        <div className="flex gap-2">
          <button onClick={() => setMkdirModal({ open: true, name: '' })} className="p-2.5 glass-card text-text-dim hover:text-white rounded-xl shadow-lg transition-all"><FolderPlus size={18} /></button>
          <button onClick={fetchFiles} disabled={loading} className="p-2.5 glass-card text-text-dim hover:text-white rounded-xl shadow-lg transition-all"><RefreshCw size={18} className={loading ? 'animate-spin' : ''} /></button>
        </div>
      </div>

      <div className="min-h-[500px] overflow-hidden">
        <table className="w-full border-separate border-spacing-y-2">
          <thead>
            <tr className="text-left text-[11px] font-black uppercase tracking-widest text-text-dim select-none">
              <th className="w-12 px-4 pb-2">
                <button onClick={toggleSelectAll} className="p-1 hover:text-primary transition-colors">
                  {selectedPaths.length === sortedFiles.length && sortedFiles.length > 0 ? <CheckSquare size={18} className="text-primary" /> : <Square size={18} />}
                </button>
              </th>
              <th className="pb-2 cursor-pointer hover:text-white transition-colors" onClick={() => toggleSort('name')}>
                <div className="flex items-center gap-2">Name {sortBy === 'name' && <ArrowUpDown size={14} className={`text-primary ${sortOrder === 'desc' ? 'rotate-180' : ''}`} />}</div>
              </th>
              <th className="pb-2 hidden md:table-cell cursor-pointer hover:text-white transition-colors" onClick={() => toggleSort('size')}>
                <div className="flex items-center gap-2">Size {sortBy === 'size' && <ArrowUpDown size={14} className={`text-primary ${sortOrder === 'desc' ? 'rotate-180' : ''}`} />}</div>
              </th>
              <th className="pb-2 hidden lg:table-cell cursor-pointer hover:text-white transition-colors" onClick={() => toggleSort('date')}>
                <div className="flex items-center gap-2">Date {sortBy === 'date' && <ArrowUpDown size={14} className={`text-primary ${sortOrder === 'desc' ? 'rotate-180' : ''}`} />}</div>
              </th>
              <th className="pb-2 text-right px-4">Menu</th>
            </tr>
          </thead>
          <tbody>
            {currentPath !== '' && (
              <tr onClick={() => setCurrentPath(currentPath.includes('/') ? currentPath.split('/').slice(0, -1).join('/') : '')} className="cursor-pointer group hover:bg-white/5 transition-all text-xs">
                <td className="py-3 px-4"><ChevronLeft size={20} className="text-primary" /></td>
                <td colSpan="4" className="py-3 font-black uppercase tracking-widest text-text-dim group-hover:text-primary">Parent Directory</td>
              </tr>
            )}

            {sortedFiles.map((item) => (
              <tr
                key={item.path}
                className={`group glass-card transition-all border-l-4 ${selectedPaths.includes(item.path) ? 'border-primary bg-primary/5' : 'border-transparent hover:bg-white/5'}`}
                onClick={() => toggleSelect(item.path)}
              >
                <td className="py-3 px-4">
                  <div className={`w-5 h-5 rounded border flex items-center justify-center transition-all ${selectedPaths.includes(item.path) ? 'bg-primary border-primary' : 'border-white/10 group-hover:border-white/30'}`}>
                    {selectedPaths.includes(item.path) && <Check size={12} strokeWidth={4} className="text-white" />}
                  </div>
                </td>
                <td className="py-3 pr-4">
                  <div className="flex items-center gap-3">
                    <div className="text-primary opacity-60 group-hover:opacity-100 transition-opacity">{getFileIcon(item)}</div>
                    <div className="min-w-0">
                      {item.is_dir ? (
                        <button onClick={(e) => { e.stopPropagation(); setCurrentPath(item.path); }} className="text-sm font-bold text-white hover:text-primary truncate block text-left w-full tracking-tight">{item.name}</button>
                      ) : (
                        <span className="text-sm font-medium text-white truncate block tracking-tight">{item.name}</span>
                      )}
                      <div className="md:hidden text-[9px] font-black uppercase text-text-dim tracking-widest mt-0.5">{item.is_dir ? 'Dir' : formatSize(item.size)} • {formatDate(item.date)}</div>
                    </div>
                  </div>
                </td>
                <td className="py-3 hidden md:table-cell text-xs font-bold text-text-dim">{item.is_dir ? '--' : formatSize(item.size)}</td>
                <td className="py-3 hidden lg:table-cell text-[11px] font-black uppercase text-text-dim">{formatDate(item.date)}</td>
                <td className="py-3 px-4 text-right">
                  <div className="flex justify-end items-center gap-1">
                    {isViewable(item) && (
                      <button
                        onClick={(e) => { e.stopPropagation(); handleView(item); }}
                        className="p-2 text-text-dim hover:text-primary hover:bg-primary/10 rounded-xl transition-all"
                        title="View/Play"
                      >
                        <Eye size={18} />
                      </button>
                    )}
                    <button
                      onClick={(e) => { e.stopPropagation(); setActiveMenu(item); }}
                      className={`p-2.5 rounded-xl transition-all ${activeMenu?.path === item.path ? 'bg-primary text-white shadow-xl' : 'text-text-dim hover:text-white hover:bg-white/10'}`}
                    >
                      <MoreVertical size={20} />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {sortedFiles.length === 0 && (
          <div className="py-32 text-center text-text-dim italic flex flex-col items-center gap-6 opacity-30">
            <Folder size={64} />
            <p className="font-black uppercase tracking-widest text-xs">No files in this folder</p>
          </div>
        )}

        {/* Multi-Delete Bar */}
        {selectedPaths.length > 0 && !activeMenu && (
          <div className="fixed bottom-24 left-4 right-4 md:left-1/2 md:-translate-x-1/2 md:w-max z-[100] animate-fade">
            <div className="glass-card bg-primary px-5 py-3 md:px-8 flex items-center justify-between gap-6 shadow-3xl rounded-2xl border-white/20">
              <div className="flex items-center gap-3 text-white">
                <div className="bg-white text-primary font-black px-3 py-1.5 rounded-lg text-xs leading-none">{selectedPaths.length}</div>
                <span className="text-xs font-black uppercase tracking-widest">Selected</span>
              </div>
              <div className="flex items-center gap-2">
                <button onClick={() => setSelectedPaths([])} className="px-3 py-2 text-white/70 hover:text-white font-black text-[11px] uppercase tracking-widest">Cancel</button>
                <button onClick={() => setDeleteModal({ open: true, type: 'bulk', paths: selectedPaths })} className="flex items-center gap-2 bg-white text-red-600 px-6 py-3 rounded-2xl font-black text-[11px] uppercase tracking-widest shadow-xl hover:scale-105 active:scale-95 transition-all">
                  <Trash2 size={16} /> Delete ALL
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default DownloadList;
