import React from 'react';
import { Layers, AlertTriangle } from 'lucide-react';

const BulkDownload = () => {
  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold flex items-center gap-2">
        <Layers className="text-primary" /> Bulk Scan & Download
      </h2>

      <div className="bg-primary/5 border border-primary/20 p-6 rounded-xl space-y-3">
        <div className="flex items-center gap-3 text-primary font-bold">
           <AlertTriangle size={20} /> Feature Coming Soon
        </div>
        <p className="text-sm text-text-dim leading-relaxed">
          The full bulk management database interface is optimized for the desktop GUI. 
          A simplified mobile-friendly scanner is being ported to the web version.
        </p>
      </div>
    </div>
  );
};

export default BulkDownload;
