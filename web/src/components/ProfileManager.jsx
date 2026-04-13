import React, { useState, useEffect } from 'react';
import { Users, Plus, Trash2, Phone, ShieldCheck, Key, ArrowRight, X, Loader2, CheckCircle2, ChevronRight, Settings } from 'lucide-react';
import Modal from './ui/Modal';

const ProfileManager = ({ profiles, activeProfile, fetchProfiles }) => {
  const [showAddModal, setShowAddModal] = useState(false);
  const [deleteModal, setDeleteModal] = useState({ open: false, phone: '' });
  const [step, setStep] = useState('phone'); 
  const [form, setForm] = useState({ phone: '', code: '', password: '', api_id: '', api_hash: '' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const resetForm = () => {
    setForm({ phone: '', code: '', password: '', api_id: '', api_hash: '' });
    setStep('phone');
    setError('');
    setLoading(false);
  };

  const startLogin = async () => {
    if (!form.phone) { setError('Phone number is required'); return; }
    setLoading(true);
    setError('');
    try {
      const res = await fetch('/api/profiles/login/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          phone: form.phone,
          api_id: form.api_id,
          api_hash: form.api_hash
        })
      });
      const data = await res.json();
      if (data.success) {
        setStep('code');
      } else {
        setError(data.error || 'Failed to start login');
      }
    } catch (e) {
      setError('Connection error');
    }
    setLoading(false);
  };

  const verifyLogin = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await fetch('/api/profiles/login/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form)
      });
      const data = await res.json();
      if (data.status === 'need_password') {
        setStep('password');
      } else if (data.success) {
        setStep('success');
        fetchProfiles();
      } else {
        setError(data.error || 'Verification failed');
      }
    } catch (e) {
      setError('Connection error');
    }
    setLoading(false);
  };

  const handleDelete = async () => {
    const phone = deleteModal.phone;
    setDeleteModal({ open: false, phone: '' });
    try {
      await fetch(`/api/profiles/${phone}`, { method: 'DELETE' });
      fetchProfiles();
    } catch (e) {}
  };

  return (
    <div className="space-y-6">
      <Modal 
        isOpen={deleteModal.open}
        title="Delete Profile"
        message={`Warning: This will permanently remove the profile +${deleteModal.phone} and terminate its Telegram session. Are you sure?`}
        onConfirm={handleDelete}
        onCancel={() => setDeleteModal({ open: false, phone: '' })}
        danger={true}
      />

      <div className="flex justify-between items-center gap-4">
        <div>
           <h2 className="text-xl md:text-2xl font-black flex items-center gap-3 tracking-tight">
             <Users className="text-primary" /> Profiles
           </h2>
           <p className="text-[10px] md:text-xs font-bold text-text-dim uppercase tracking-widest mt-1">Manage Telegram Sessions</p>
        </div>
        <button 
          onClick={() => { resetForm(); setShowAddModal(true); }}
          className="btn-primary flex items-center gap-2 px-6 py-2 shadow-xl shadow-primary/20"
        >
          <Plus size={18} /> <span className="hidden sm:inline">Add Profile</span>
        </button>
      </div>

      <div className="space-y-3">
        {profiles.map((phone) => (
          <div key={phone} className={`glass-card p-4 transition-all border-l-4 ${activeProfile === phone ? 'border-primary bg-primary/5' : 'border-transparent hover:border-white/5'}`}>
            <div className="flex items-center justify-between gap-4">
               <div className="flex items-center gap-4 min-w-0">
                  <div className={`w-10 h-10 rounded-xl flex items-center justify-center transition-colors ${activeProfile === phone ? 'bg-primary text-white shadow-lg' : 'bg-white/5 text-text-dim'}`}>
                     <Phone size={20} />
                  </div>
                  <div className="min-w-0">
                     <h3 className="font-bold text-sm md:text-base tracking-tight truncate">+{phone}</h3>
                     <div className="flex items-center gap-2 mt-0.5">
                        {activeProfile === phone ? (
                          <span className="text-[9px] font-black uppercase text-primary tracking-widest flex items-center gap-1.5 animate-pulse">
                            <div className="w-1.5 h-1.5 rounded-full bg-primary" /> Currently Active
                          </span>
                        ) : (
                          <span className="text-[9px] font-black uppercase text-text-dim tracking-widest opacity-40">Standby</span>
                        )}
                     </div>
                  </div>
               </div>

               <button 
                 onClick={() => setDeleteModal({ open: true, phone })}
                 className="p-3 text-text-dim hover:text-red-500 hover:bg-red-500/10 rounded-xl transition-all flex-shrink-0"
                 title="Delete Profile"
               >
                 <Trash2 size={20} />
               </button>
            </div>
          </div>
        ))}
      </div>

      {profiles.length === 0 && (
        <div className="py-24 text-center glass-card border-dashed border-white/10 flex flex-col items-center gap-6 opacity-60">
           <Users size={48} className="text-text-dim opacity-20" />
           <p className="font-black uppercase tracking-[0.2em] text-xs text-text-dim">No sessions found</p>
           <button 
             onClick={() => { resetForm(); setShowAddModal(true); }}
             className="btn-primary mt-2"
           >
              Setup First Profile
           </button>
        </div>
      )}

      {/* Add Profile Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-[200] flex items-center justify-center p-4 bg-black/60 backdrop-blur-md">
           <div className="glass-card w-full max-w-md p-8 shadow-3xl animate-fade relative overflow-y-auto max-h-[90vh]">
              <button 
                onClick={() => setShowAddModal(false)}
                className="absolute top-6 right-6 p-2 hover:bg-white/5 rounded-full text-text-dim"
              >
                <X size={20} />
              </button>

              <div className="mb-8 text-center">
                 <div className="w-16 h-16 bg-primary/10 rounded-3xl flex items-center justify-center text-primary mx-auto mb-4">
                    {step === 'phone' && <Phone size={32} />}
                    {step === 'code' && <ShieldCheck size={32} />}
                    {step === 'password' && <Key size={32} />}
                    {step === 'success' && <CheckCircle2 size={32} />}
                 </div>
                 <h2 className="text-2xl font-black tracking-tight">
                    {step === 'phone' && 'Connect Account'}
                    {step === 'code' && 'Verification'}
                    {step === 'password' && '2-Step Auth'}
                    {step === 'success' && 'Authorized'}
                 </h2>
                 <p className="text-text-dim text-sm mt-1">
                    {step === 'phone' && 'Enter your Telegram details to continue'}
                    {step === 'code' && `Verify the code sent to your Telegram`}
                    {step === 'password' && 'Enter your cloud password'}
                    {step === 'success' && 'Profile successfully connected'}
                 </p>
              </div>

              {error && (
                <div className="mb-6 p-4 bg-red-500/10 border border-red-500/20 text-red-500 rounded-2xl text-xs font-bold flex items-center gap-3">
                   <X size={16} className="shrink-0" /> {error}
                </div>
              )}

              <div className="space-y-4">
                 {step === 'phone' && (
                    <>
                       <div className="space-y-2">
                          <label className="text-[10px] font-black uppercase text-text-dim tracking-widest pl-1">Phone Number</label>
                          <input 
                            autoFocus
                            className="input-field text-xl tracking-tight py-4" 
                            placeholder="+1234567890"
                            value={form.phone}
                            onChange={(e) => setForm({...form, phone: e.target.value})}
                          />
                       </div>

                       <div className="pt-2 border-t border-white/5 mt-4">
                          <div className="flex items-center gap-2 mb-4">
                             <Settings size={14} className="text-primary" />
                             <span className="text-[9px] font-black uppercase tracking-widest text-text-dim">API Credentials (Optional if set in .env)</span>
                          </div>
                          
                          <div className="grid grid-cols-1 gap-4">
                             <div className="space-y-2">
                                <label className="text-[10px] font-black uppercase text-text-dim tracking-widest pl-1">API ID</label>
                                <input 
                                  className="input-field text-sm py-3" 
                                  placeholder="1234567"
                                  value={form.api_id}
                                  onChange={(e) => setForm({...form, api_id: e.target.value})}
                                />
                             </div>
                             <div className="space-y-2">
                                <label className="text-[10px] font-black uppercase text-text-dim tracking-widest pl-1">API Hash</label>
                                <input 
                                  className="input-field text-sm py-3" 
                                  placeholder="abc123def456..."
                                  value={form.api_hash}
                                  onChange={(e) => setForm({...form, api_hash: e.target.value})}
                                />
                             </div>
                          </div>
                       </div>
                    </>
                 )}

                 {(step === 'code' || step === 'password') && (
                    <div className="space-y-2">
                       <label className="text-[10px] font-black uppercase text-text-dim tracking-widest pl-1">
                          {step === 'code' ? 'Code' : 'Password'}
                       </label>
                       <input 
                         autoFocus
                         type={step === 'password' ? 'password' : 'text'}
                         className="input-field text-xl tracking-widest text-center py-4" 
                         placeholder={step === 'code' ? '12345' : '••••••••'}
                         value={step === 'code' ? form.code : form.password}
                         onChange={(e) => setForm({...form, [step === 'code' ? 'code' : 'password']: e.target.value})}
                         onKeyDown={(e) => e.key === 'Enter' && verifyLogin()}
                       />
                    </div>
                 )}

                 {step !== 'success' && (
                    <button 
                      onClick={step === 'phone' ? startLogin : verifyLogin}
                      disabled={loading}
                      className="w-full btn-primary py-4 uppercase font-black tracking-[0.2em] flex items-center justify-center gap-3 text-sm shadow-xl shadow-primary/20"
                    >
                      {loading ? (
                         <Loader2 size={24} className="animate-spin" />
                      ) : (
                         <>Continue <ArrowRight size={20} /></>
                      )}
                    </button>
                 )}

                 {step === 'success' && (
                    <button 
                      onClick={() => setShowAddModal(false)}
                      className="w-full btn-primary bg-green-600 hover:bg-green-500 py-4 uppercase font-black tracking-[0.2em] text-sm"
                    >
                       Done
                    </button>
                 )}

                 {step !== 'phone' && step !== 'success' && (
                    <button 
                      onClick={resetForm}
                      className="w-full py-2 text-text-dim hover:text-white text-[10px] font-black uppercase tracking-widest transition-all"
                    >
                       Reset
                    </button>
                 )}
              </div>
           </div>
        </div>
      )}
    </div>
  );
};

export default ProfileManager;
