import React, { useState, useEffect } from 'react';

const API = 'http://127.0.0.1:5000/api';

export default function App() {
  const [page, setPage] = useState('user'); 
  return (
    <div style={styles.appBg}>
      <div style={styles.container}>
        <nav style={styles.nav}>
          <button onClick={() => setPage('user')} style={page === 'user' ? styles.btnActive : styles.btnInactive}>Submit Feedback</button>
          <button onClick={() => setPage('admin')} style={page === 'admin' ? styles.btnActive : styles.btnInactive}>Admin Dashboard</button>
        </nav>
        {page === 'user' ? <UserPage /> : <AdminDashboard />}
      </div>
    </div>
  );
}

function UserPage() {
  const [text, setText] = useState('');
  const [msg, setMsg] = useState('');
  const [loading, setLoading] = useState(false);
  const [attachedFile, setAttachedFile] = useState(null);

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) setAttachedFile(e.target.files[0]);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!text.trim() && !attachedFile) {
      alert("Please provide issue details in text or attach a file.");
      return;
    }
    setLoading(true); setMsg('');
    const formData = new FormData();
    if (text.trim()) formData.append("text", text.trim());
    if (attachedFile) formData.append("file", attachedFile);

    try {
      const res = await fetch(`${API}/tickets/submit`, { method: 'POST', body: formData });
      const data = await res.json();
      if (res.ok) {
        setMsg(data.message || 'Submitted successfully.');
        setText(''); setAttachedFile(null);
      } else {
        setMsg('Error. Please try submitting again.');
      }
    } catch {
      setMsg('Error. Please try submitting again.');
    }
    setLoading(false);
  };

  return (
    <div style={styles.card}>
      <h2 style={styles.h2}>Raise a Support Ticket</h2>
      <p style={{ color: '#94a3b8', marginBottom: '20px' }}>Submit text, upload single/batch tickets or attach an error screenshot.</p>
      <form onSubmit={handleSubmit}>
        <textarea rows={5} value={text} onChange={(e) => setText(e.target.value)} placeholder="Describe your issue in detail..." style={styles.input} />
        <div style={styles.controlRow}>
          <div style={styles.fileControlBox}>
            <label style={styles.uploadBtn}>
              [+] Attach File
              <input type="file" onChange={handleFileChange} style={{ display: 'none' }} />
            </label>
            {attachedFile && (
              <div style={styles.previewBox}>
                <span style={{ color: '#94a3b8', fontSize: '14px' }}>{attachedFile.name}</span>
                <button type="button" onClick={() => setAttachedFile(null)} style={styles.discardBtn}>Remove</button>
              </div>
            )}
          </div>
        </div>
        <button type="submit" disabled={loading} style={styles.primaryBtn}>{loading ? 'Submitting...' : 'Submit Feedback'}</button>
      </form>
      {msg && <p style={{ color: msg.includes('Error') ? '#ef4444' : '#32cd32', marginTop: '20px' }}>{msg}</p>}
    </div>
  );
}

function AdminDashboard() {
  const [data, setData] = useState(null);
  const [syncing, setSyncing] = useState(false);
  const [selectedLLM, setSelectedLLM] = useState('gemini');

  // Pagination State
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 5;

  const fetchStats = async () => {
    try {
      const res = await fetch(`${API}/admin/summary`);
      setData(await res.json());
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => { fetchStats(); }, []);

  const handleSync = async () => {
    setSyncing(true);
    try {
      const res = await fetch(`${API}/tickets/sync`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider: selectedLLM })
      });
      const newData = await res.json();
      if (newData.metrics) {
        setData(newData);
      } else {
        fetchStats();
      }
    } catch (err) {
      console.error("Sync error:", err);
    } finally {
      setSyncing(false);
    }
  };

  const solve = async (id) => {
    await fetch(`${API}/tickets/${id}/solve`, { method: 'POST' });
    fetchStats();
  };

  const actionItems = data?.critical_tickets || [];
  const totalPages = Math.ceil(actionItems.length / itemsPerPage) || 1;
  const currentItems = actionItems.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage);

  return (
    <div>
      {/* Model Selection Card */}
      <div style={styles.card}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
          <label style={{ color: '#94a3b8', fontWeight: 'bold', fontSize: '14px' }}>Active Inference Model:</label>
          <select
            value={selectedLLM}
            onChange={(e) => setSelectedLLM(e.target.value)}
            style={styles.selectInput}
          >
            <option value="gemini">Google Gemini 3.5 Flash (Cloud API)</option>
            <option value="groq">Groq Llama 3.1 8B (Fast Cloud API)</option>
            <option value="huggingface">Hugging Face (Qwen 2.5 7B)</option>
          </select>
        </div>
      </div>

      <div style={styles.headerRow}>
        <h2 style={styles.h2}>Analytics Dashboard</h2>
        <button onClick={handleSync} disabled={syncing} style={syncing ? styles.syncBtnDisabled : styles.syncBtn}>
          {syncing ? 'Processing AI Batch...' : 'Sync Pending Tickets'}
        </button>
      </div>

      {data?.metrics && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '30px' }}>
          {/* JUST NOW PROCESSED */}
          <div style={{ backgroundColor: '#1e293b', padding: '20px', borderRadius: '12px', borderLeft: '4px solid #f59e0b' }}>
            <h3 style={{ color: '#f8fafc', margin: '0 0 15px 0', fontSize: '18px' }}>Processed Just Now</h3>
            <div style={{ display: 'flex', justifyContent: 'space-between', color: '#94a3b8', fontSize: '14px', fontWeight: 'bold' }}>
              <span>Total: <span style={{color: '#f8fafc'}}>{data.metrics.just_now.Total}</span></span>
              <span style={{color: '#ef4444'}}>Crit: {data.metrics.just_now.Critical}</span>
              <span style={{color: '#f97316'}}>High: {data.metrics.just_now.High}</span>
              <span style={{color: '#eab308'}}>Med: {data.metrics.just_now.Medium}</span>
              <span style={{color: '#32cd32'}}>Low: {data.metrics.just_now.Low}</span>
            </div>
          </div>

          {/* OVERALL LIFETIME */}
          <div style={{ backgroundColor: '#1e293b', padding: '20px', borderRadius: '12px', borderLeft: '4px solid #3b82f6' }}>
            <h3 style={{ color: '#f8fafc', margin: '0 0 15px 0', fontSize: '18px' }}>Overall Lifetime</h3>
            <div style={{ display: 'flex', justifyContent: 'space-between', color: '#94a3b8', fontSize: '14px', fontWeight: 'bold' }}>
              <span>Total: <span style={{color: '#f8fafc'}}>{data.metrics.lifetime.Total}</span></span>
              <span style={{color: '#ef4444'}}>Crit: {data.metrics.lifetime.Critical}</span>
              <span style={{color: '#f97316'}}>High: {data.metrics.lifetime.High}</span>
              <span style={{color: '#eab308'}}>Med: {data.metrics.lifetime.Medium}</span>
              <span style={{color: '#32cd32'}}>Low: {data.metrics.lifetime.Low}</span>
            </div>
          </div>
        </div>
      )}

      {actionItems.length > 0 && (
        <div style={styles.card}>
          <h3 style={styles.h2}>Action Required: High / Critical</h3>
          <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '10px' }}>
            <thead style={{ color: '#94a3b8', textAlign: 'left' }}>
              <tr>
                <th style={{ paddingBottom: '10px' }}>Mark Solved</th>
                <th style={{ paddingBottom: '10px' }}>ID</th>
                <th style={{ paddingBottom: '10px' }}>Priority</th>
                <th style={{ paddingBottom: '10px' }}>Category</th>
                <th style={{ paddingBottom: '10px' }}>Customer Issue</th>
              </tr>
            </thead>
            <tbody>
              {currentItems.map((t) => (
                <tr key={t.id} style={{ color: '#e2e8f0', borderBottom: '1px solid #1e293b' }}>
                  <td style={{ padding: '12px' }}>
                    <input type="checkbox" onChange={() => solve(t.id)} style={{ transform: 'scale(1.4)' }} />
                  </td>
                  <td style={{ padding: '12px' }}>#{t.id}</td>
                  <td style={{ padding: '12px', color: t.priority === 'Critical' ? '#ef4444' : '#32cd32', fontWeight: 'bold' }}>{t.priority}</td>
                  <td style={{ padding: '12px' }}>{t.category}</td>
                  <td style={{ padding: '12px' }}>
                    <div style={{ marginBottom: '8px' }}>{t.ai_summary || t.description || t.subject}</div>
                    {t.file_url && (
                      <a href={t.file_url} target="_blank" rel="noopener noreferrer" style={styles.linkBtn}>[View Attached File]</a>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          
          {/* Pagination Controls */}
          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '20px', color: '#94a3b8' }}>
            <button 
              onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))} 
              disabled={currentPage === 1}
              style={currentPage === 1 ? styles.pageBtnDisabled : styles.pageBtn}
            >
              Previous
            </button>
            <span>Page {currentPage} of {totalPages}</span>
            <button 
              onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))} 
              disabled={currentPage >= totalPages}
              style={currentPage >= totalPages ? styles.pageBtnDisabled : styles.pageBtn}
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

const styles = {
  appBg: { backgroundColor: '#0a1128', minHeight: '100vh', color: '#e2e8f0', fontFamily: 'sans-serif', margin: 0, padding: '40px 20px' },
  container: { maxWidth: '900px', margin: '0 auto' },
  nav: { display: 'flex', gap: '15px', marginBottom: '30px', borderBottom: '1px solid #1e293b', paddingBottom: '15px' },
  btnActive: { padding: '8px 16px', color: '#32cd32', background: 'none', border: 'none', fontSize: '16px', cursor: 'pointer', fontWeight: 'bold', textShadow: '0 0 10px rgba(50, 205, 50, 0.6)' },
  btnInactive: { padding: '8px 16px', color: '#94a3b8', background: 'none', border: 'none', fontSize: '16px', cursor: 'pointer' },
  card: { backgroundColor: '#111827', padding: '30px', borderRadius: '8px', border: '1px solid #1e293b', marginBottom: '30px' },
  h2: { margin: '0 0 15px 0', color: '#f8fafc' },
  input: { width: '100%', padding: '15px', boxSizing: 'border-box', marginBottom: '15px', borderRadius: '6px', border: '1px solid #334155', backgroundColor: '#1e293b', color: '#f8fafc', outline: 'none' },
  selectInput: { padding: '10px 14px', borderRadius: '4px', backgroundColor: '#1e293b', color: '#32cd32', border: '1px solid #32cd32', outline: 'none', fontWeight: 'bold' },
  controlRow: { display: 'flex', gap: '20px', marginBottom: '20px', flexWrap: 'wrap' },
  fileControlBox: { display: 'flex', alignItems: 'center', gap: '15px' },
  uploadBtn: { padding: '10px 18px', backgroundColor: '#1e293b', color: '#32cd32', border: '1px solid #32cd32', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold', display: 'inline-block' },
  previewBox: { display: 'flex', alignItems: 'center', gap: '10px' },
  discardBtn: { padding: '6px 12px', backgroundColor: 'transparent', color: '#ef4444', border: '1px solid #ef4444', borderRadius: '4px', cursor: 'pointer', fontSize: '12px' },
  primaryBtn: { padding: '12px 24px', cursor: 'pointer', backgroundColor: '#32cd32', color: '#000', border: 'none', borderRadius: '4px', fontSize: '16px', fontWeight: 'bold', boxShadow: '0 0 10px rgba(50, 205, 50, 0.3)' },
  headerRow: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '30px' },
  syncBtn: { padding: '10px 20px', backgroundColor: 'transparent', color: '#32cd32', border: '1px solid #32cd32', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' },
  syncBtnDisabled: { padding: '10px 20px', backgroundColor: '#334155', color: '#94a3b8', border: '1px solid #334155', borderRadius: '4px', cursor: 'not-allowed' },
  linkBtn: { display: 'inline-block', padding: '4px 8px', backgroundColor: '#1e293b', color: '#3b82f6', borderRadius: '4px', textDecoration: 'none', fontSize: '13px', fontWeight: 'bold', border: '1px solid #334155' },
  pageBtn: { padding: '6px 12px', backgroundColor: '#1e293b', color: '#f8fafc', border: '1px solid #334155', borderRadius: '4px', cursor: 'pointer' },
  pageBtnDisabled: { padding: '6px 12px', backgroundColor: 'transparent', color: '#475569', border: '1px solid #334155', borderRadius: '4px', cursor: 'not-allowed' }
};