import React, { useState, useEffect, useRef } from 'react';
import { Layers, Search, Play, Pause, Square, Trash2, Folder, CheckSquare, Square as SquareIcon, ArrowUpDown, ChevronLeft, ChevronRight, Clock, Filter, List, Database, HardDrive, FileText, Download, Upload, X } from 'lucide-react';
import Modal from './ui/Modal';
import TreeModal from './ui/TreeModal';

const BulkDownload = ({ activeProfile, tasks, refreshCounter, onRemoveTask }) => {
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
  const [treeModal, setTreeModal] = useState({ open: false, action: '', src: [] });
  const lastTaskStatus = useRef({});
  const fileInputRef = useRef(null);

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
    Object.entries(tasks).forEach(([id, t]) => {
      const isRelevant = id.startsWith('scan') || id.startsWith('bulk');
      if (isRelevant) {
        const isDone = t.status === 'done' && lastTaskStatus.current[id] !== 'done';
        if (isDone) fetchItems();
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
      setModal({ open: true, title: 'Scan Error', message: e.message });
    }
  };

  const handleSetLocation = (dst) => {
    setLocation(dst);
    const { action, src } = treeModal;
    if (action === 'bulk') startBulkDownload(dst, src);
    setTreeModal({ open: false, action: '', src: [] });
  };

  const startBulkDownload = async (dst, src) => {
    try {
      await fetch('/api/bulk/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          profile: activeProfile,
          ids: src,
          location: dst,
          delay: [parseInt(delay.min), parseInt(delay.max)]
        })
      });
    } catch (e) {
      setModal({ open: true, title: 'Error', message: 'Failed to start download' });
    }
  };

  const handleTaskAction = async (action, taskId) => {
    await fetch(`/api/download/${action}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task_id: taskId })
    });
  };

  const handleRemoveTask = async (taskId) => {
    if (onRemoveTask) onRemoveTask(taskId);
    else await fetch(`/api/tasks/remove/${taskId}`, { method: 'POST' });
  };

  const handleExportTxt = () => {
    const ids = selectedIds.length > 0 ? selectedIds.join(',') : '';
    window.location.href = `/api/bulk/export/txt?profile=${activeProfile}&ids=${ids}`;
  };

  const handleExportJson = () => {
    const ids = selectedIds.length > 0 ? selectedIds.join(',') : '';
    window.location.href = `/api/bulk/export/json?profile=${activeProfile}&ids=${ids}`;
  };

  const handleImportJson = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    try {
      const res = await fetch(`/api/bulk/import?profile=${activeProfile}`, { 
        method: 'POST', 
        body: formData 
      });
      if (res.ok) fetchItems();
    } catch (e) { }
  };

  const handleDeleteSelected = () => {
    if (selectedIds.length === 0) return;
    setModal({
      open: true,
      title: 'Delete Selected',
      message: `Are you sure you want to delete ${selectedIds.length} selected items?`,
      onConfirm: async () => {
        try {
          await fetch('/api/bulk/delete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ profile: activeProfile, ids: selectedIds })
          });
          setSelectedIds([]);
          fetchItems();
          setModal({ open: false });
        } catch (e) { }
      }
    });
  };

  const handleResetStatus = async () => {
    if (selectedIds.length === 0) return;
    try {
      await fetch('/api/bulk/status', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ profile: activeProfile, ids: selectedIds, status: 'pending' })
      });
      setSelectedIds([]);
      fetchItems();
    } catch (e) { }
  };

  const handleClearDb = () => {
    setModal({
      open: true,
      title: 'Clear Database',
      message: 'Are you sure you want to clear all scanned items for this profile?',
      onConfirm: async () => {
        await fetch('/api/bulk/delete', {
          method: 'DELETE',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ profile: activeProfile })
        });
        fetchItems();
        setModal({ open: false });
      }
    });
  };

  const toggleSelect = (id) => {
    setSelectedIds(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]);
  };

  const toggleSelectAll = () => {
    if (selectedIds.length === items.length) setSelectedIds([]);
    else setSelectedIds(items.map(it => it.id));
  };

  const handleSort = (col) => {
    if (sortBy === col) setSortOrder(sortOrder === 'DESC' ? 'ASC' : 'DESC');
    else { setSortBy(col); setSortOrder('ASC'); }
    setPage(0);
  };

  const formatSize = (bytes) => {
    if (!bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const progressTasks = Object.entries(tasks)
    .filter(([id, t]) => (id.startsWith('bulk') || id.startsWith('scan')) && (!t.profile || t.profile === activeProfile))
    .reverse();

  return (
    <div className="flex flex-col lg:flex-row gap-8 items-start">
      <Modal
        isOpen={modal.open}
        title={modal.title}
        message={modal.message}
        onConfirm={modal.onConfirm || (() => setModal({ ...modal, open: false }))}
        onCancel={() => setModal({ ...modal, open: false })}
      />
      <TreeModal
        isOpen={treeModal.open}
        title="Select Destination"
        onSelect={handleSetLocation}
        onClose={() => setTreeModal({ ...treeModal, open: false })}
      />

      {/* Left Column: List and Progress */}
      <div className="w-full lg:w-2/3 space-y-8 order-2 lg:order-1">
        {progressTasks.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {progressTasks.map(([id, t]) => (
              <div key={id} className="glass-card p-4 border-primary/20 bg-primary/5 animate-fade flex flex-col gap-3">
                <div className="flex justify-between items-center">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-primary/20 rounded-lg text-primary">
                      {id.startsWith('scan') ? <Search size={18} /> : <Layers size={18} />}
                    </div>
                    <div>
                      <h4 className="text-xs font-black uppercase tracking-wider text-white">
                        {id.startsWith('scan') ? 'Channel Scanner' : 'Bulk Downloader'}
                      </h4>
                      <p className="text-[10px] text-text-dim font-bold">{t.status}</p>
                    </div>
                  </div>
                  <div className="flex gap-1">
                    {['done', 'failed', 'cancelled'].includes(t.status) ? (
                      <button onClick={() => handleRemoveTask(id)} className="p-1.5 hover:bg-white/10 rounded-lg text-text-dim hover:text-white" title="Dismiss">
                        <X size={14} />
                      </button>
                    ) : (
                      <>
                        {!id.startsWith('scan') && (
                          t.status === 'paused' ?
                            <button onClick={() => handleTaskAction('resume', id)} className="p-1.5 hover:bg-white/10 rounded-lg text-green-500"><Play size={12} fill="currentColor" /></button> :
                            <button onClick={() => handleTaskAction('pause', id)} className="p-1.5 hover:bg-white/10 rounded-lg text-yellow-500"><Pause size={12} fill="currentColor" /></button>
                        )}
                        <button onClick={() => handleTaskAction('cancel', id)} className="p-1.5 hover:bg-white/10 rounded-lg text-red-500"><Square size={12} fill="currentColor" /></button>
                      </>
                    )}
                  </div>
                </div>
                  <div className="space-y-1.5">
                    <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
                       <div className="h-full bg-primary transition-all duration-500 shadow-[0_0_10px_rgba(0,120,212,0.5)]" style={{ width: `${t.progress}%` }}></div>
                    </div>
                    <div className="flex flex-col gap-1 text-[10px] font-bold">
                       <div className="flex justify-between items-center">
                          <p className="text-white truncate flex-1 mr-2">{t.text.split(' | ')[0]}</p>
                          <span className="text-primary">{Math.round(t.progress)}%</span>
                       </div>
                       {t.text.includes(' | ') && (
                         <div className="flex justify-between items-center text-text-dim/80">
                            <span>{t.text.split(' | ')[1]}</span>
                            <span>{t.text.split(' | ')[2]}</span>
                         </div>
                       )}
                    </div>
                  </div>
              </div>
            ))}
          </div>
        )}

        <div className="space-y-4">
          <div className="flex justify-between items-end px-2">
            <div className="space-y-1">
              <h2 className="text-xl font-black text-white flex items-center gap-3">
                <List size={20} className="text-primary" /> Scan Results
              </h2>
              <p className="text-xs text-text-dim font-bold uppercase tracking-widest">
                {total} Items found • {selectedIds.length} Selected
              </p>
            </div>
            <div className="flex items-center gap-3">
              {selectedIds.length > 0 && (
                <div className="flex items-center gap-2 animate-fade">
                  <button 
                    onClick={handleDeleteSelected}
                    className="flex items-center gap-2 px-4 py-2 bg-red-500/10 text-red-500 hover:bg-red-500 hover:text-white rounded-xl text-[10px] font-black uppercase tracking-widest transition-all border border-red-500/20 shadow-lg shadow-red-500/5"
                  >
                    <Trash2 size={14} /> Delete ({selectedIds.length})
                  </button>
                  <button 
                    onClick={handleResetStatus}
                    className="flex items-center gap-2 px-4 py-2 bg-primary/10 text-primary hover:bg-primary hover:text-white rounded-xl text-[10px] font-black uppercase tracking-widest transition-all border border-primary/20 shadow-lg shadow-primary/5"
                  >
                    <Clock size={14} /> Reset Status
                  </button>
                </div>
              )}
              <div className="flex items-center gap-3 bg-white/5 px-3 py-2 rounded-xl border border-white/5">
                <Filter size={14} className="text-primary" />
                <select value={viewFilter} onChange={(e) => setViewFilter(e.target.value)} className="bg-transparent border-none text-[10px] font-black uppercase text-white outline-none cursor-pointer focus:ring-0">
                  <option value="All" className="bg-[#0d0e12]">All Status</option>
                  <option value="pending" className="bg-[#0d0e12]">Pending</option>
                  <option value="completed" className="bg-[#0d0e12]">Completed</option>
                </select>
              </div>
            </div>
          </div>

          <div className="glass-card overflow-hidden border-white/5 shadow-2xl">
            <div className="overflow-x-auto custom-scrollbar">
              <table className="w-full text-left border-collapse min-w-[700px]">
                <thead>
                  <tr className="bg-white/5 border-b border-white/5">
                    <th className="p-4 w-10">
                      <button onClick={toggleSelectAll} className={`w-5 h-5 rounded border-2 transition-all flex items-center justify-center ${selectedIds.length === items.length && items.length > 0 ? 'bg-primary border-primary' : 'border-white/20 hover:border-primary/50'}`}>
                        {selectedIds.length === items.length && items.length > 0 && <CheckSquare size={14} className="text-white" />}
                      </button>
                    </th>
                    <th onClick={() => handleSort('message_id')} className="p-4 text-[10px] font-black uppercase tracking-widest text-text-dim cursor-pointer hover:text-primary transition-all"><div className="flex items-center gap-2">ID <ArrowUpDown size={12} /></div></th>
                    <th onClick={() => handleSort('type')} className="p-4 text-[10px] font-black uppercase tracking-widest text-text-dim cursor-pointer hover:text-primary transition-all"><div className="flex items-center gap-2">Type <ArrowUpDown size={12} /></div></th>
                    <th onClick={() => handleSort('name')} className="p-4 text-[10px] font-black uppercase tracking-widest text-text-dim cursor-pointer hover:text-primary transition-all"><div className="flex items-center gap-2">Name <ArrowUpDown size={12} /></div></th>
                    <th onClick={() => handleSort('size')} className="p-4 text-[10px] font-black uppercase tracking-widest text-text-dim cursor-pointer hover:text-primary transition-all"><div className="flex items-center gap-2">Size <ArrowUpDown size={12} /></div></th>
                    <th onClick={() => handleSort('status')} className="p-4 text-[10px] font-black uppercase tracking-widest text-text-dim cursor-pointer hover:text-primary transition-all"><div className="flex items-center gap-2">Status <ArrowUpDown size={12} /></div></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {loading ? (
                    <tr><td colSpan="6" className="p-20 text-center text-xs font-bold uppercase tracking-widest text-text-dim animate-pulse">Loading items...</td></tr>
                  ) : items.length === 0 ? (
                    <tr><td colSpan="6" className="p-20 text-center text-text-dim italic text-sm">No items found. Start a scan to populate this list.</td></tr>
                  ) : items.map(item => (
                    <tr key={item.id} className={`hover:bg-white/5 transition-all cursor-pointer ${selectedIds.includes(item.id) ? 'bg-primary/5' : ''}`} onClick={() => toggleSelect(item.id)}>
                      <td className="p-4"><div className={`w-5 h-5 rounded border-2 transition-all flex items-center justify-center ${selectedIds.includes(item.id) ? 'bg-primary border-primary' : 'border-white/10'}`}>{selectedIds.includes(item.id) && <CheckSquare size={14} className="text-white" />}</div></td>
                      <td className="p-4 text-xs font-mono text-text-dim">{item.message_id}</td>
                      <td className="p-4 text-xs font-bold uppercase text-primary/70">{item.type}</td>
                      <td className="p-4 text-xs font-medium text-white max-w-[200px] truncate">{item.name || 'Unnamed Media'}</td>
                      <td className="p-4 text-xs text-text-dim font-bold">{formatSize(item.size)}</td>
                      <td className="p-4"><span className={`text-[10px] px-2 py-1 rounded-full font-black uppercase tracking-widest ${item.status === 'completed' ? 'bg-green-500/10 text-green-500' : item.status === 'pending' ? 'bg-yellow-500/10 text-yellow-500' : 'bg-red-500/10 text-red-500'}`}>{item.status}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="bg-[#12141a] p-4 flex justify-between items-center text-[10px] font-black uppercase tracking-widest text-text-dim">
              <span>Showing {page * pageSize + 1} - {Math.min((page + 1) * pageSize, total)} of {total}</span>
              <div className="flex gap-2">
                <button disabled={page === 0} onClick={() => setPage(page - 1)} className="p-2 glass-card hover:border-primary disabled:opacity-30 transition-all rounded-lg"><ChevronLeft size={16} /></button>
                <button disabled={(page + 1) * pageSize >= total} onClick={() => setPage(page + 1)} className="p-2 glass-card hover:border-primary disabled:opacity-30 transition-all rounded-lg"><ChevronRight size={16} /></button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Right Column: Control Center */}
      <div className="w-full lg:w-1/3 space-y-6 order-1 lg:order-2 lg:sticky lg:top-10">
        <div className="glass-card p-6 border-primary/20 space-y-6 shadow-3xl bg-[#0d0e12]/80 backdrop-blur-xl">
          <h3 className="text-xl font-black text-white flex items-center gap-3"><Database size={20} className="text-primary" /> Control Center</h3>
          <div className="space-y-4">
            <div className="space-y-2">
              <label className="text-[10px] font-black uppercase tracking-widest text-text-dim px-1">Channel Source</label>
              <div className="relative flex items-center">
                <Search size={16} className="absolute left-4 text-primary pointer-events-none" />
                <input
                  type="text"
                  placeholder="t.me/channel_name"
                  className="input-field"
                  style={{ paddingLeft: '44px' }}
                  value={channel}
                  onChange={(e) => setChannel(e.target.value)}
                />
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-[10px] font-black uppercase tracking-widest text-text-dim px-1">Start Point (Optional)</label>
              <input type="text" placeholder="Message ID or Link" className="input-field" value={startPoint} onChange={(e) => setStartPoint(e.target.value)} />
            </div>
            <div className="flex items-center gap-3 px-1">
              <label className="text-[10px] font-bold text-text-dim uppercase tracking-widest">Delay (S):</label>
              <input type="number" className="w-16 bg-bg-dark border border-white/10 rounded-lg p-1.5 text-xs text-center font-bold text-white outline-none" value={delay.min} onChange={(e) => setDelay({ ...delay, min: e.target.value })} />
              <span className="text-text-dim">-</span>
              <input type="number" className="w-16 bg-bg-dark border border-white/10 rounded-lg p-1.5 text-xs text-center font-bold text-white outline-none" value={delay.max} onChange={(e) => setDelay({ ...delay, max: e.target.value })} />
            </div>
          </div>
          <div className="space-y-3">
            <label className="text-[10px] font-black uppercase tracking-widest text-text-dim px-1">Include Content</label>
            <div className="grid grid-cols-2 gap-2">
              {Object.keys(filters).map(f => (
                <button key={f} onClick={() => setFilters({ ...filters, [f]: !filters[f] })} className={`flex items-center justify-between p-3 rounded-xl border transition-all ${filters[f] ? 'bg-primary/20 border-primary text-primary' : 'bg-white/5 border-white/5 text-text-dim'}`}>
                  <span className="text-xs font-black uppercase">{f}s</span>
                  {filters[f] && <CheckSquare size={14} />}
                </button>
              ))}
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3 pt-2">
            <button onClick={() => handleScan('new')} className="btn-primary py-4 text-xs font-black tracking-widest uppercase flex flex-col items-center gap-1"><ChevronRight size={16} /> Scan Newer</button>
            <button onClick={() => handleScan('old')} className="bg-white/5 hover:bg-white/10 border border-white/10 text-white py-4 rounded-xl text-xs font-black tracking-widest uppercase transition-all flex flex-col items-center gap-1"><ChevronLeft size={16} /> Scan Older</button>
            <button onClick={() => setTreeModal({ open: true, action: 'bulk', src: selectedIds })} disabled={!activeProfile || (total === 0 && selectedIds.length === 0)} className="col-span-2 btn-primary py-4 text-sm font-black uppercase flex items-center justify-center gap-3 disabled:opacity-30 disabled:grayscale"><Download size={18} /> Start Download {selectedIds.length > 0 && `(${selectedIds.length})`}</button>
          </div>
          <hr className="border-white/5" />
          <div className="space-y-3">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <button onClick={handleExportTxt} className="p-3 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl text-[10px] font-black uppercase text-text-dim hover:text-white transition-all flex items-center justify-center gap-2"><FileText size={14} /> Export TXT</button>
              <button onClick={handleExportJson} className="p-3 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl text-[10px] font-black uppercase text-text-dim hover:text-white transition-all flex items-center justify-center gap-2"><Database size={14} /> Export JSON</button>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <button onClick={() => fileInputRef.current.click()} className="p-3 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl text-[10px] font-black uppercase text-text-dim hover:text-white transition-all flex items-center justify-center gap-2"><Upload size={14} /> Import JSON<input type="file" ref={fileInputRef} onChange={handleImportJson} className="hidden" accept=".json" /></button>
              <button onClick={handleClearDb} className="p-3 bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 rounded-xl text-[10px] font-black uppercase text-red-500 transition-all flex items-center justify-center gap-2"><Trash2 size={14} /> Clear Database</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default BulkDownload;
