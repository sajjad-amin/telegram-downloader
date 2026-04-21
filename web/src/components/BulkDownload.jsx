import React, { useState, useEffect, useRef } from 'react';
import { Layers, Search, Play, Pause, Square, Trash2, Folder, CheckSquare, Square as SquareIcon, ArrowUpDown, ChevronLeft, ChevronRight, Clock, Filter, List, Database, HardDrive, FileText, Download, Upload } from 'lucide-react';
import Modal from './ui/Modal';
import TreeModal from './ui/TreeModal';

const BulkDownload = ({ activeProfile, tasks, refreshCounter }) => {
  const [channel, setChannel] = useState('');
  const [startPoint, setStartPoint] = useState('');
  const [filters, setFilters] = useState({ video: true, audio: false, photo: false, file: false });
  const [delay, setDelay] = useState({ min: 5, max: 15 });
  const [location, setLocation] = useState('');
  
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [pageSize] = useState(100);
  const [loading, setLoading] = useState(false);
  const [selectedIds, setSelectedIds] = useState([]);
  
  const [sortBy, setSortBy] = useState('message_id');
  const [sortOrder, setSortOrder] = useState('DESC');
  const [viewFilter, setViewFilter] = useState('All');
  const [typeFilter, setTypeFilter] = useState('All');

  const [modal, setModal] = useState({ open: false, title: '', message: '', onConfirm: null });
  const [confirmModal, setConfirmModal] = useState({ open: false, title: '', message: '', onConfirm: null });
  const [treeModalOpen, setTreeModalOpen] = useState(false);
  const lastTaskStatus = useRef({});

  const fetchItems = async () => {
    if (!activeProfile) return;
    setLoading(true);
    try {
      const params = new URLSearchParams({
        profile: activeProfile,
        limit: pageSize,
        offset: page * pageSize,
        sort: sortBy,
        order: sortOrder,
        status: viewFilter,
        type: typeFilter
      });
      const res = await fetch(`/api/bulk/items?${params}`);
      const data = await res.json();
      setItems(data.items);
      setTotal(data.total);
    } catch (e) { }
    setLoading(false);
  };

  useEffect(() => {
    fetchItems();
  }, [activeProfile, page, sortBy, sortOrder, viewFilter, typeFilter, refreshCounter]);

  useEffect(() => {
    // Live refresh when a scan or bulk task completes
    Object.entries(tasks).forEach(([id, t]) => {
      const isRelevant = id.startsWith('scan') || id.startsWith('bulk');
      if (isRelevant) {
        const isDone = t.status === 'done' && lastTaskStatus.current[id] !== 'done';
        if (isDone) {
          fetchItems();
        }
        lastTaskStatus.current[id] = t.status;
      }
    });
  }, [tasks]);

  const handleScan = async (direction) => {
    if (!channel || !activeProfile) return;
    try {
      const activeFilters = Object.keys(filters).filter(k => filters[k]);
      const res = await fetch('/api/bulk/scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          profile: activeProfile,
          channel,
          filters: activeFilters,
          direction,
          start_point: startPoint
        })
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error || 'Scan failed');
      }
      setPage(0);
      fetchItems();
    } catch (e) {
      setModal({ open: true, title: 'Scan Error', message: e.message, type: 'alert' });
    }
  };

  const handleStartBulk = async () => {
    if (!activeProfile) return;
    try {
      const res = await fetch('/api/bulk/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          profile: activeProfile,
          ids: selectedIds,
          location,
          delay: [parseInt(delay.min), parseInt(delay.max)]
        })
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error || 'Failed to start bulk download');
      }
      setSelectedIds([]);
    } catch(e) {
      setModal({ open: true, title: 'Bulk Error', message: e.message, type: 'alert' });
    }
  };

  const handleClearDb = () => {
    setConfirmModal({
      open: true,
      title: 'Clear Database',
      message: "Are you sure you want to clear ALL fetched items from this profile's database?",
      onConfirm: async () => {
        await fetch(`/api/bulk/delete?profile=${activeProfile}`, {
          method: 'DELETE'
        });
        setConfirmModal({ ...confirmModal, open: false });
        fetchItems();
      }
    });
  };

  const handleDeleteSelected = () => {
    if (selectedIds.length === 0) return;
    setConfirmModal({
      open: true,
      title: 'Delete Selected',
      message: `Are you sure you want to delete ${selectedIds.length} items from the list?`,
      onConfirm: async () => {
        await fetch(`/api/bulk/delete`, {
          method: 'DELETE',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ profile: activeProfile, ids: selectedIds })
        });
        setSelectedIds([]);
        setConfirmModal({ ...confirmModal, open: false });
        fetchItems();
      }
    });
  };

  const handleExportTxt = () => {
    let url = `/api/bulk/export/txt?profile=${activeProfile}`;
    if (selectedIds.length > 0) url += `&ids=${selectedIds.join(',')}`;
    window.location.href = url;
  };

  const handleExportJson = () => {
    let url = `/api/bulk/export/json?profile=${activeProfile}`;
    if (selectedIds.length > 0) url += `&ids=${selectedIds.join(',')}`;
    window.location.href = url;
  };

  const handleImportJson = () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    input.onchange = async (e) => {
      const file = e.target.files[0];
      if (!file) return;
      const formData = new FormData();
      formData.append('file', file);
      const res = await fetch(`/api/bulk/import?profile=${activeProfile}`, {
        method: 'POST',
        body: formData
      });
      if (res.ok) {
        const data = await res.json();
        setModal({ open: true, title: 'Import Success', message: `Successfully imported ${data.count} items.`, type: 'alert' });
        fetchItems();
      }
    };
    input.click();
  };

  const handleTaskAction = async (action, taskId) => {
    await fetch(`/api/download/${action}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task_id: taskId })
    });
  };

  const progressTasks = Object.entries(tasks)
    .filter(([id, t]) => (id.startsWith('bulk') || id.startsWith('scan')) && (!t.profile || t.profile === activeProfile))
    .reverse();

  const toggleSelect = (id) => {
    setSelectedIds(prev => prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]);
  };

  const formatSize = (bytes) => {
    if (!bytes) return '--';
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return parseFloat((bytes / Math.pow(1024, i)).toFixed(1)) + ' ' + sizes[i];
  };

  return (
    <div className="space-y-8 pb-10">
      <Modal isOpen={modal.open} title={modal.title} message={modal.message} type="alert" onConfirm={() => setModal({ ...modal, open: false })} onCancel={() => setModal({ ...modal, open: false })} />
      <Modal isOpen={confirmModal.open} title={confirmModal.title} message={confirmModal.message} type="confirm" onConfirm={confirmModal.onConfirm} onCancel={() => setConfirmModal({ ...confirmModal, open: false })} />
      <TreeModal isOpen={treeModalOpen} title="Select Download Folder" onSelect={(path) => { setLocation(path); setTreeModalOpen(false); }} onClose={() => setTreeModalOpen(false)} />

      {/* Header Section */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center text-primary">
             <Layers size={22} />
          </div>
          <div>
            <h2 className="text-xl font-black text-white tracking-tight">Bulk Downloader</h2>
            <p className="text-[10px] font-bold text-text-dim uppercase tracking-widest leading-none">Automated Channel Scraper</p>
          </div>
        </div>
      </div>

      {/* Scanner Control Panel */}
      <div className="glass-card grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 p-6 border-white/5 shadow-2xl">
        <div className="space-y-2 md:col-span-2">
          <label className="text-[10px] font-black uppercase tracking-widest text-text-dim flex items-center gap-2 px-1">
             <Search size={12} className="text-primary" /> Channel Username / URL
          </label>
          <input 
            type="text" 
            placeholder="e.g. @ChannelName or t.me/xxx"
            className="input-field"
            value={channel}
            onChange={(e) => setChannel(e.target.value)}
          />
        </div>
        
        <div className="space-y-2 lg:col-span-1">
          <label className="text-[10px] font-black uppercase tracking-widest text-text-dim flex items-center gap-2 px-1">
             <Clock size={12} className="text-primary" /> Scan From (Optional ID)
          </label>
          <input 
            type="text" 
            placeholder="Message ID or Link"
            className="input-field"
            value={startPoint}
            onChange={(e) => setStartPoint(e.target.value)}
          />
        </div>

        <div className="flex items-end gap-2">
          <button onClick={() => handleScan('new')} className="flex-1 btn-primary py-3.5 tracking-tight font-black text-xs">SCAN NEWER</button>
          <button onClick={() => handleScan('old')} className="flex-1 btn-primary bg-bg-dark border-border hover:bg-white/5 py-3.5 tracking-tight font-black text-xs text-white">SCAN OLDER</button>
        </div>
      </div>

      {/* Filters & Options */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="glass-card p-5 border-white/5 space-y-4">
           <h3 className="text-[10px] font-black uppercase tracking-widest text-text-dim px-1 flex items-center gap-2">
             <Filter size={12} className="text-primary" /> Filter Media Types
           </h3>
           <div className="grid grid-cols-2 gap-3">
             {Object.keys(filters).map(f => (
               <button 
                key={f} 
                onClick={() => setFilters({...filters, [f]: !filters[f]})}
                className={`flex items-center gap-3 p-3 rounded-xl border transition-all ${filters[f] ? 'bg-primary/10 border-primary text-primary' : 'bg-transparent border-white/5 text-text-dim hover:text-white hover:border-white/20'}`}
               >
                 <div className={`w-4 h-4 rounded flex items-center justify-center border ${filters[f] ? 'bg-primary border-primary' : 'border-current'}`}>
                    {filters[f] && <CheckSquare size={10} className="text-white" />}
                 </div>
                 <span className="text-[11px] font-black uppercase tracking-widest">{f}s</span>
               </button>
             ))}
           </div>
        </div>

        <div className="glass-card p-5 border-white/5 space-y-4">
           <h3 className="text-[10px] font-black uppercase tracking-widest text-text-dim px-1 flex items-center gap-2">
             <HardDrive size={12} className="text-primary" /> Download Destination
           </h3>
           <div className="flex flex-col gap-3">
             <div className="flex gap-2">
               <div className="flex-grow glass-card border-white/5 p-3 px-4 text-xs font-medium text-white truncate bg-[#0d0e12]">
                 {location || 'Select a folder...'}
               </div>
               <button 
                onClick={() => setTreeModalOpen(true)}
                className="p-3 glass-card hover:border-primary transition-all rounded-xl"
               >
                 <Folder size={18} />
               </button>
             </div>
             <div className="flex items-center gap-3 px-1">
               <label className="text-[10px] font-bold text-text-dim uppercase tracking-widest">Delay (S):</label>
               <input type="number" className="w-16 bg-bg-dark border border-white/10 rounded-lg p-1.5 text-xs text-center font-bold text-white" value={delay.min} onChange={(e) => setDelay({...delay, min: e.target.value})} />
               <span className="text-text-dim">-</span>
               <input type="number" className="w-16 bg-bg-dark border border-white/10 rounded-lg p-1.5 text-xs text-center font-bold text-white" value={delay.max} onChange={(e) => setDelay({...delay, max: e.target.value})} />
             </div>
           </div>
        </div>

        <div className="glass-card p-5 border-white/5 flex flex-col justify-center gap-4">
           <button 
            disabled={true && (!activeProfile || (total === 0 && selectedIds.length === 0))} 
            onClick={handleStartBulk}
            className="w-full flex items-center justify-center gap-3 py-5 bg-primary hover:bg-primary-hover disabled:opacity-30 disabled:grayscale transition-all rounded-2xl shadow-xl shadow-primary/20 text-white"
           >
              <Play size={20} fill="currentColor" />
              <div className="text-left">
                <span className="block text-sm font-black uppercase tracking-tighter leading-none">Start Bulk Download</span>
                <span className="block text-[9px] font-bold opacity-60 uppercase tracking-widest mt-1">
                  {selectedIds.length > 0 ? `Download ${selectedIds.length} Selected` : `Download All Pending (${total})`}
                </span>
              </div>
           </button>
           <div className="grid grid-cols-2 gap-2 mt-2">
             <button 
              onClick={handleExportTxt} 
              className="flex items-center justify-center gap-2 py-2.5 glass-card border-white/5 hover:border-primary/50 text-[10px] font-black uppercase tracking-widest text-text-dim hover:text-primary transition-all"
              title={selectedIds.length > 0 ? "Export selected to TXT" : "Export all to TXT"}
             >
                <FileText size={12} /> TXT Export
             </button>
             <button 
              onClick={handleExportJson} 
              className="flex items-center justify-center gap-2 py-2.5 glass-card border-white/5 hover:border-primary/50 text-[10px] font-black uppercase tracking-widest text-text-dim hover:text-primary transition-all"
              title={selectedIds.length > 0 ? "Export selected to JSON" : "Export all to JSON"}
             >
                <Download size={12} /> JSON Export
             </button>
             <button 
              onClick={handleImportJson} 
              className="flex items-center justify-center gap-2 py-2.5 glass-card border-white/5 hover:border-primary/50 text-[10px] font-black uppercase tracking-widest text-text-dim hover:text-primary transition-all"
             >
                <Upload size={12} /> Import JSON
             </button>
             <button 
              onClick={handleClearDb} 
              className="flex items-center justify-center gap-2 py-2.5 glass-card border-white/5 hover:border-red-500/50 text-[10px] font-black uppercase tracking-widest text-text-dim hover:text-red-500 transition-all text-center"
             >
                <Trash2 size={12} /> Clear Database
             </button>
           </div>
         </div>
      </div>

      {/* Active Scan/Bulk Tasks */}
      {progressTasks.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-[10px] font-black text-text-dim uppercase tracking-widest px-1">Ongoing Operations</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {progressTasks.map(([id, t]) => (
              <div key={id} className="glass-card p-5 border-primary/20 bg-primary/5 animate-fade-in relative overflow-hidden group shadow-lg">
                 <div className="flex justify-between items-start mb-4">
                    <div className="flex items-center gap-3">
                       <div className="w-8 h-8 bg-primary/20 rounded-lg flex items-center justify-center text-primary">
                          {id.startsWith('scan') ? <Search size={16} /> : <Layers size={16} />}
                       </div>
                       <div>
                          <span className="block text-xs font-black text-white uppercase tracking-tighter">
                            {id.startsWith('scan') ? 'Channel Scanner' : 'Bulk Downloader'}
                          </span>
                          <span className="block text-[8px] font-bold text-primary uppercase tracking-[0.2em] mt-0.5">{t.status}</span>
                       </div>
                    </div>
                    <div className="flex gap-1">
                       {!id.startsWith('scan') && (
                         t.status === 'paused' ? 
                         <button onClick={() => handleTaskAction('resume', id)} className="p-1.5 hover:bg-white/10 rounded-lg text-green-500"><Play size={12} fill="currentColor"/></button> :
                         <button onClick={() => handleTaskAction('pause', id)} className="p-1.5 hover:bg-white/10 rounded-lg text-yellow-500"><Pause size={12} fill="currentColor"/></button>
                       )}
                       <button onClick={() => handleTaskAction('cancel', id)} className="p-1.5 hover:bg-white/10 rounded-lg text-red-500"><Square size={12} fill="currentColor"/></button>
                    </div>
                 </div>
                 
                 <div className="h-1.5 bg-white/5 rounded-full overflow-hidden mb-3">
                    <div className="h-full bg-primary transition-all duration-300 shadow-[0_0_10px_rgba(0,132,255,0.5)]" style={{ width: `${t.progress}%` }}></div>
                 </div>
                 
                 <div className="flex justify-between items-end">
                    <div className="min-w-0 pr-4">
                       <span className="block text-[10px] font-bold text-text-dim uppercase tracking-widest mb-1">Status</span>
                       <span className="block text-[11px] font-black text-white truncate max-w-[180px] sm:max-w-xs">{t.text}</span>
                    </div>
                    <div className="text-right shrink-0">
                       <span className="block text-xl font-black text-primary leading-none tracking-tighter">{Math.round(t.progress)}%</span>
                    </div>
                 </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Database View Section */}
      <div className="space-y-4">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 px-1">
          <div className="flex items-center gap-3">
             <List size={18} className="text-primary" />
             <h3 className="text-[10px] font-black uppercase tracking-widest text-text-dim">Scanned Items Database ({total})</h3>
          </div>
          
          <div className="flex flex-wrap gap-3 items-center w-full md:w-auto">
             <div className="flex items-center gap-2 glass-card p-1.5 px-3 border-white/5">
                <Filter size={12} className="text-primary" />
                <select className="bg-transparent border-none text-[10px] font-black uppercase text-white outline-none cursor-pointer" value={viewFilter} onChange={(e) => setViewFilter(e.target.value)}>
                   <option value="All">All Items</option>
                   <option value="pending">Pending</option>
                   <option value="completed">Completed</option>
                   <option value="failed">Failed</option>
                   <option value="downloading">In Progress</option>
                </select>
             </div>
             
             <button onClick={handleDeleteSelected} disabled={selectedIds.length === 0} className="flex items-center gap-2 px-3 py-2 bg-red-500/10 text-red-500 rounded-lg text-[10px] font-black uppercase tracking-widest hover:bg-red-500 hover:text-white transition-all disabled:opacity-30 disabled:grayscale">
                <Trash2 size={12} /> Delete Selection ({selectedIds.length})
             </button>
          </div>
        </div>

        <div className="glass-card border-white/5 overflow-hidden shadow-2xl">
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead className="bg-[#12141a]">
                <tr className="text-[10px] font-bold text-text-dim uppercase tracking-widest border-b border-white/5">
                  <th className="p-4 w-12">
                     <button onClick={() => setSelectedIds(selectedIds.length === items.length ? [] : items.map(it => it.id))} className="text-primary hover:text-white transition-all">
                       {selectedIds.length === items.length && items.length > 0 ? <CheckSquare size={16} /> : <SquareIcon size={16} />}
                     </button>
                  </th>
                  <th className="p-4 cursor-pointer hover:text-white" onClick={() => { setSortBy('message_id'); setSortOrder(sortOrder === 'DESC' ? 'ASC' : 'DESC'); }}>
                    <div className="flex items-center gap-2">ID {sortBy === 'message_id' && (sortOrder === 'DESC' ? '↓' : '↑')}</div>
                  </th>
                  <th className="p-4 cursor-pointer hover:text-white" onClick={() => { setSortBy('type'); setSortOrder(sortOrder === 'DESC' ? 'ASC' : 'DESC'); }}>
                    <div className="flex items-center gap-2">Type {sortBy === 'type' && (sortOrder === 'DESC' ? '↓' : '↑')}</div>
                  </th>
                  <th className="p-4 cursor-pointer hover:text-white" onClick={() => { setSortBy('name'); setSortOrder(sortOrder === 'DESC' ? 'ASC' : 'DESC'); }}>
                    <div className="flex items-center gap-2">Name {sortBy === 'name' && (sortOrder === 'DESC' ? '↓' : '↑')}</div>
                  </th>
                  <th className="p-4 cursor-pointer hover:text-white" onClick={() => { setSortBy('size'); setSortOrder(sortOrder === 'DESC' ? 'ASC' : 'DESC'); }}>
                    <div className="flex items-center gap-2">Size {sortBy === 'size' && (sortOrder === 'DESC' ? '↓' : '↑')}</div>
                  </th>
                  <th className="p-4 cursor-pointer hover:text-white" onClick={() => { setSortBy('status'); setSortOrder(sortOrder === 'DESC' ? 'ASC' : 'DESC'); }}>
                    <div className="flex items-center gap-2">Status {sortBy === 'status' && (sortOrder === 'DESC' ? '↓' : '↑')}</div>
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {items.length === 0 && !loading && (
                  <tr>
                    <td colSpan="6" className="p-20 text-center text-text-dim italic text-xs">
                       <Database size={40} className="mx-auto mb-4 opacity-10" />
                       No records found. Scan a channel to build your download list.
                    </td>
                  </tr>
                )}
                {items.map(it => (
                  <tr key={it.id} className={`group hover:bg-white/5 transition-all cursor-pointer ${selectedIds.includes(it.id) ? 'bg-primary/5' : ''}`} onClick={() => toggleSelect(it.id)}>
                    <td className="p-4">
                       <div className={`w-4 h-4 rounded border flex items-center justify-center transition-all ${selectedIds.includes(it.id) ? 'bg-primary border-primary' : 'border-white/10 group-hover:border-white/30'}`}>
                          {selectedIds.includes(it.id) && <CheckSquare size={10} className="text-white" />}
                       </div>
                    </td>
                    <td className="p-4 text-xs font-bold text-white">{it.message_id}</td>
                    <td className="p-4"><span className="text-[9px] font-black uppercase px-2 py-0.5 rounded bg-white/5 text-text-dim">{it.type}</span></td>
                    <td className="p-4 text-xs font-medium text-white truncate max-w-[200px]">{it.name}</td>
                    <td className="p-4 text-xs font-bold text-text-dim uppercase tracking-tighter">{formatSize(it.size)}</td>
                    <td className="p-4">
                       <span className={`text-[9px] font-black uppercase px-2 py-0.5 rounded ${
                         it.status === 'completed' ? 'bg-green-500/20 text-green-500' : 
                         it.status === 'failed' ? 'bg-red-500/20 text-red-500' :
                         it.status === 'downloading' ? 'bg-primary/20 text-primary' : 'bg-white/10 text-text-dim'
                       }`}>
                         {it.status}
                       </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="bg-[#12141a] p-4 flex flex-col md:flex-row justify-between items-center gap-4 text-[10px] font-black uppercase tracking-widest text-text-dim">
             <div className="flex items-center gap-4">
                <span>Showing {page * pageSize + 1} - {Math.min((page + 1) * pageSize, total)} of {total}</span>
             </div>
             <div className="flex items-center gap-3">
                <button 
                  disabled={page === 0} 
                  onClick={() => setPage(page - 1)}
                  className="p-2 glass-card hover:border-primary disabled:opacity-30 disabled:grayscale transition-all rounded-lg"
                >
                  <ChevronLeft size={16} />
                </button>
                <div className="flex items-center gap-1">
                   {Array.from({ length: Math.min(5, Math.ceil(total / pageSize)) }).map((_, i) => {
                     // Simple pagination window
                     const pageNum = i; 
                     return (
                       <button 
                         key={i} 
                         onClick={() => setPage(pageNum)}
                         className={`w-8 h-8 rounded-lg font-black transition-all ${page === pageNum ? 'bg-primary text-white' : 'hover:bg-white/5'}`}
                       >
                         {pageNum + 1}
                       </button>
                     );
                   })}
                </div>
                <button 
                  disabled={(page + 1) * pageSize >= total} 
                  onClick={() => setPage(page + 1)}
                  className="p-2 glass-card hover:border-primary disabled:opacity-30 disabled:grayscale transition-all rounded-lg"
                >
                  <ChevronRight size={16} />
                </button>
             </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default BulkDownload;
