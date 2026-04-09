import { useState, useEffect } from 'react';
import { FileText, Download, Trash2, Eye, X, RefreshCw, AlertCircle, Calendar } from 'lucide-react';
import ApiService from '../services/api';

const Reports = () => {
  const [reports, setReports] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Modal state
  const [selectedReport, setSelectedReport] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const fetchReports = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await ApiService.getReports();
      if (response.status === 'success') {
        setReports(response.reports);
      } else {
        throw new Error(response.error || 'Failed to fetch reports');
      }
    } catch (err) {
      setError(err.message || 'Error communicating with the server.');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchReports();
  }, []);

  const handleDownload = (report) => {
    const blob = new Blob([report.content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    
    // Auto-append extension if missing from name
    const extension = report.format === 'json' ? '.json' : '.txt';
    let filename = report.name;
    if (!filename.endsWith(extension) && report.format) {
       filename += extension;
    }
    
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleView = (report) => {
    setSelectedReport(report);
  };

  const closeModal = () => {
    setSelectedReport(null);
  };

  const handleDelete = async (reportId) => {
    if (!window.confirm('Are you sure you want to delete this report? This action cannot be undone.')) {
      return;
    }

    try {
      const response = await ApiService.deleteReport(reportId);
      if (response.status === 'success') {
        const successMessage = document.createElement('div');
        successMessage.className = 'fixed top-4 right-4 bg-green-500 text-white px-6 py-3 rounded-lg shadow-lg z-50';
        successMessage.textContent = 'Report deleted successfully!';
        document.body.appendChild(successMessage);
        
        setTimeout(() => {
          document.body.removeChild(successMessage);
        }, 3000);
        
        setReports(reports.filter(r => r.id !== reportId));
      } else {
        throw new Error(response.error || 'Failed to delete report');
      }
    } catch (err) {
      alert('Error deleting report: ' + err.message);
    }
  };

  const getFormatBadge = (format) => {
    switch ((format || '').toLowerCase()) {
      case 'json':
        return <span className="px-2 py-1 text-xs font-medium text-yellow-500 bg-yellow-500/10 rounded-full border border-yellow-500/20 uppercase">JSON</span>;
      case 'txt':
        return <span className="px-2 py-1 text-xs font-medium text-blue-500 bg-blue-500/10 rounded-full border border-blue-500/20 uppercase">TXT</span>;
      case 'pdf':
        return <span className="px-2 py-1 text-xs font-medium text-red-500 bg-red-500/10 rounded-full border border-red-500/20 uppercase">PDF</span>;
      default:
        return <span className="px-2 py-1 text-xs font-medium text-gray-400 bg-gray-500/10 rounded-full border border-gray-500/20 uppercase">{format || 'UNKWN'}</span>;
    }
  };

  const getTypeBadge = (type) => {
    switch ((type || '').toLowerCase()) {
      case 'diff':
        return <span className="text-purple-400">Schema Diff</span>;
      case 'validation':
        return <span className="text-emerald-400">Validation Run</span>;
      case 'schema':
        return <span className="text-sky-400">API Schema</span>;
      default:
        return <span className="text-gray-400 capitalize">{type}</span>;
    }
  };

  return (
    <div className="p-8">
      <div className="max-w-5xl mx-auto">
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-white mb-2">Saved Reports</h1>
            <p className="text-gray-400">View and manage your downloaded reports and schemas</p>
          </div>
          <button 
            onClick={fetchReports}
            className="flex items-center space-x-2 text-sm bg-slate-800 hover:bg-slate-700 text-white px-4 py-2 rounded-lg transition-colors border border-slate-700"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>

        {error && (
          <div className="glass-card p-4 mb-6 border-l-4 border-red-500">
            <div className="flex items-center space-x-3">
              <AlertCircle className="w-5 h-5 text-red-400" />
              <span className="text-red-400">{error}</span>
            </div>
          </div>
        )}

        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-20 text-gray-400">
            <RefreshCw className="w-8 h-8 animate-spin mb-4 text-orange-500" />
            <p>Loading reports...</p>
          </div>
        ) : reports.length === 0 ? (
           <div className="glass-card p-12 text-center border border-dashed border-gray-700">
             <FileText className="w-16 h-16 text-gray-600 mx-auto mb-4" />
             <h3 className="text-xl font-semibold text-white mb-2">No Reports Found</h3>
             <p className="text-gray-400 max-w-md mx-auto">
               You haven't saved any reports yet. Reports generated in Version Check and Schema Validate will appear here.
             </p>
           </div>
        ) : (
          <div className="space-y-4">
            {reports.map((report) => (
              <div key={report.id} className="glass-card p-5 border border-slate-800/80 hover:border-slate-700 transition-colors flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                <div className="flex items-start space-x-4 flex-1">
                  <div className="bg-slate-800/50 p-3 rounded-lg border border-slate-700/50 mt-1 md:mt-0">
                    <FileText className="w-6 h-6 text-orange-500" />
                  </div>
                  <div>
                    <h3 className="text-lg font-bold text-white mb-1 truncate max-w-lg" title={report.name}>
                      {report.name}
                    </h3>
                    <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-gray-400">
                      <div className="flex items-center font-medium">
                        {getTypeBadge(report.type)}
                      </div>
                      <div className="flex items-center space-x-1.5">
                        <Calendar className="w-3.5 h-3.5 text-gray-500" />
                        <span>{new Date(report.created_at).toLocaleString()}</span>
                      </div>
                      {report.api_id && (
                        <div className="text-xs px-2 py-0.5 rounded bg-slate-800/80 text-slate-300">
                          API #{report.api_id}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
                
                <div className="flex items-center gap-2 w-full md:w-auto mt-2 md:mt-0 pt-3 md:pt-0 border-t md:border-t-0 border-slate-800">
                  <div className="mr-3 hidden sm:block">
                    {getFormatBadge(report.format)}
                  </div>
                  
                  <button
                    onClick={() => handleView(report)}
                    className="flex-1 md:flex-none flex justify-center items-center space-x-1.5 bg-sky-500/10 text-sky-400 hover:bg-sky-500/20 px-3 py-2 rounded-md transition-colors text-sm font-medium border border-sky-500/20"
                  >
                    <Eye className="w-4 h-4" />
                    <span>View</span>
                  </button>
                  
                  <button
                    onClick={() => handleDownload(report)}
                    className="flex-1 md:flex-none flex justify-center items-center space-x-1.5 bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20 px-3 py-2 rounded-md transition-colors text-sm font-medium border border-emerald-500/20"
                  >
                    <Download className="w-4 h-4" />
                    <span>Download</span>
                  </button>
                  
                  <button
                    onClick={() => handleDelete(report.id)}
                    className="p-2 bg-red-500/10 text-red-500 hover:bg-red-500/20 rounded-md transition-colors border border-red-500/20"
                    title="Delete report"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* View Modal */}
      {selectedReport && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" onClick={closeModal} />
          <div className="relative w-full max-w-4xl max-h-[90vh] bg-slate-900 border border-slate-700 rounded-xl shadow-2xl flex flex-col">
            <div className="flex items-center justify-between p-4 flex-shrink-0 border-b border-slate-800">
               <div>
                 <h2 className="text-xl font-semibold text-white">{selectedReport.name}</h2>
                 <p className="text-xs text-gray-400 mt-1">Generated: {new Date(selectedReport.created_at).toLocaleString()}</p>
               </div>
               <div className="flex items-center space-x-2">
                 <button 
                  onClick={() => handleDownload(selectedReport)}
                  className="p-2 text-gray-400 hover:text-emerald-400 hover:bg-slate-800 rounded-lg transition-colors"
                  title="Download File"
                 >
                   <Download className="w-5 h-5" />
                 </button>
                 <button 
                  onClick={closeModal}
                  className="p-2 text-gray-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
                 >
                   <X className="w-5 h-5" />
                 </button>
               </div>
            </div>
            
            <div className="p-4 flex-1 overflow-auto">
              <pre className="font-mono text-sm text-gray-300 bg-black/50 p-6 rounded-lg whitespace-pre-wrap word-break-all border border-slate-800">
                {selectedReport.content}
              </pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Reports;
