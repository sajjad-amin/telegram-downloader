import React, { useState, useEffect } from 'react';
import { Routes, Route, Link, useLocation } from 'react-router-dom';
import { Download, Layers, Users, Folder, LogOut } from 'lucide-react';
import SingleDownload from './SingleDownload';
import BulkDownload from './BulkDownload';
import ProfileManager from './ProfileManager';
import DownloadList from './DownloadList';
import Modal from './ui/Modal';
import io from 'socket.io-client';

// Connect to the backend (5001) if we are in dev mode (5173), otherwise use the same origin
const SOCKET_URL = window.location.port === '5173' 
  ? `${window.location.protocol}//${window.location.hostname}:5001`
  : '/';

const socket = io(SOCKET_URL, {
  transports: ['websocket', 'polling'],
  autoConnect: true,
  reconnection: true,
  reconnectionAttempts: 10,
  reconnectionDelay: 2000
});

// Defensive error handling for Proxy/Cloudflare issues
socket.on('connect_error', (err) => {
  console.error("Socket Connection Error:", err.message);
  // If websocket fails, try falling back explicitly
  if (err.message === "xhr poll error") {
    socket.io.opts.transports = ["polling"];
  }
});

const Dashboard = () => {
  const location = useLocation();
  const [profiles, setProfiles] = useState([]);
  const [activeProfile, setActiveProfile] = useState(localStorage.getItem('selected_profile') || '');
  const [tasks, setTasks] = useState({});
  const [showLogoutModal, setShowLogoutModal] = useState(false);

  useEffect(() => {
    fetchProfiles();
    fetchTasks();

    socket.on('progress', (data) => {
      setTasks(prev => ({
        ...prev,
        [data.task_id]: {
          progress: data.progress,
          text: data.text,
          status: data.status,
          profile: data.profile
        }
      }));
    });

    return () => socket.off('progress');
  }, []);

  useEffect(() => {
    if (activeProfile) {
      localStorage.setItem('selected_profile', activeProfile);
    }
  }, [activeProfile]);

  const fetchProfiles = async () => {
    try {
      const res = await fetch('/api/profiles');
      const data = await res.json();
      setProfiles(data);
      if (data.length > 0 && !activeProfile) {
        setActiveProfile(data[0]);
      }
    } catch (e) { }
  };

  const fetchTasks = async () => {
    try {
      const res = await fetch('/api/tasks');
      const data = await res.json();
      setTasks(data);
    } catch (e) { }
  };

  const handleLogout = async () => {
    await fetch('/api/auth/logout', { method: 'POST' });
    localStorage.removeItem('selected_profile');
    window.location.href = '/login';
  };

  const TABS = [
    { id: 'single', path: '/', label: 'Single', icon: <Download size={18} /> },
    { id: 'bulk', path: '/bulk', label: 'Bulk', icon: <Layers size={18} /> },
    { id: 'downloads', path: '/downloads', label: 'Files', icon: <Folder size={18} /> },
    { id: 'profiles', path: '/profiles', label: 'Profiles', icon: <Users size={18} /> },
  ];

  const isActive = (path) => {
    if (path === '/' && location.pathname === '/') return true;
    if (path !== '/' && location.pathname.startsWith(path)) return true;
    return false;
  };

  return (
    <div className="w-full min-h-screen pb-12 lg:pb-0 px-4 md:px-8 py-6 md:py-10">
      <Modal
        isOpen={showLogoutModal}
        title="Logout"
        message="Are you sure you want to log out?"
        onConfirm={handleLogout}
        onCancel={() => setShowLogoutModal(false)}
      />

      <header className="flex flex-col md:flex-row justify-between items-start md:items-center mb-10 gap-6">
        <div>
          <h1 className="text-2xl md:text-4xl font-black text-white tracking-tight leading-none mb-2">Telegram Downloader</h1>
        </div>

        <div className="flex items-center gap-3 w-full md:w-auto">
          <div className="flex flex-1 md:flex-none items-center gap-3 glass-card p-2 px-4 shadow-xl border-primary/10">
            <Users size={14} className="text-primary" />
            <select
              value={activeProfile}
              onChange={(e) => setActiveProfile(e.target.value)}
              className="bg-transparent border-none text-white font-bold text-xs md:text-sm outline-none cursor-pointer focus:ring-0 flex-grow"
            >
              {profiles.length === 0 && <option value="">No Profile</option>}
              {profiles.map(p => <option key={p} value={p} className="bg-card-bg">{p}</option>)}
            </select>
          </div>

          <button
            onClick={() => setShowLogoutModal(true)}
            className="p-3 glass-card hover:border-red-500/50 hover:text-red-500 transition-all rounded-xl shadow-xl border-white/5"
            title="Sign Out"
          >
            <LogOut size={20} />
          </button>
        </div>
      </header>

      <div className="flex flex-col md:flex-row gap-8 lg:gap-12">
        {/* Navigation Sidebar / Bottom Bar on Mobile */}
        <aside className="fixed bottom-0 left-0 right-0 z-50 md:relative md:w-60 flex-shrink-0">
          <nav className="flex md:flex-col gap-1 p-2 md:p-0 backdrop-blur-xl bg-bg-dark/80 md:bg-transparent border-t md:border-none border-white/10">
            {TABS.map(tab => (
              <Link
                key={tab.id}
                to={tab.path}
                className={`flex flex-1 md:flex-none flex-col md:flex-row items-center gap-1.5 md:gap-3.5 p-2.5 md:py-4 md:px-6 rounded-xl transition-all ${isActive(tab.path)
                    ? 'bg-primary text-white shadow-2xl shadow-primary/20 scale-100'
                    : 'text-text-dim hover:text-white md:hover:bg-white/5'
                  }`}
              >
                <div className={`${isActive(tab.path) ? 'text-white' : 'text-primary opacity-60'}`}>
                  {tab.icon}
                </div>
                <span className="text-[10px] md:text-sm font-bold md:font-extrabold tracking-tight uppercase md:normal-case md:tracking-normal">{tab.label}</span>
              </Link>
            ))}
          </nav>
        </aside>

        <main className="flex-grow animate-fade">
          <div className="glass-card p-6 md:p-10 min-h-[500px] border-white/5 shadow-3xl">
            <Routes>
              <Route path="/" element={<SingleDownload activeProfile={activeProfile} tasks={tasks} />} />
              <Route path="/bulk" element={<BulkDownload activeProfile={activeProfile} tasks={tasks} />} />
              <Route path="/downloads/*" element={<DownloadList />} />
              <Route path="/profiles" element={<ProfileManager profiles={profiles} activeProfile={activeProfile} fetchProfiles={fetchProfiles} />} />
            </Routes>
          </div>
        </main>
      </div>
    </div>
  );
};

export default Dashboard;
