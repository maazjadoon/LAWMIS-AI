import React, { useState, useEffect, useRef } from 'react';

interface Message {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
}

interface Doc {
  id: string;
  name: string;
  path: string;
  type: 'pdf' | 'pptx';
  timestamp: string;
}

export default function App() {
  const [activeTab, setActiveTab] = useState<'chat' | 'dashboard' | 'documents'>('chat');
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      sender: 'assistant',
      text: "Welcome to the LAWMIS Assistant. Query workshops, active licenses, payment challans, emissions, or drag a PDF/PPTX here to perform deep analytical document query.",
    }
  ]);
  const [chatInput, setChatInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [sessionId] = useState(() => `session_${Math.random().toString(36).substring(2, 11)}`);
  
  // File Q&A Attachment states
  const [attachedFile, setAttachedFile] = useState<{ name: string; path: string; type: string } | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  // KPI Dashboard data
  const [kpi] = useState<any>({
    workshops: { total: '100', active: '100', pending: '0', rejected: '0' },
    licenses: { total: '100', active: '100', expired: '0', expiring_soon: '0' },
    payments: { total_revenue: '1,002,500', paid_count: '100', pending_count: '0' },
    emissions: { total: '47,230', pass_rate: '48.9%', fail_rate: '15.7%' },
    cities: [
      { city: 'Khuzdar', count: 11 },
      { city: 'Quetta', count: 11 },
      { city: 'Turbat', count: 10 },
      { city: 'Karachi', count: 9 },
      { city: 'Lahore', count: 9 },
    ]
  });

  // History of generated/uploaded documents
  const [documents, setDocuments] = useState<Doc[]>([]);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  // Load KPI metrics from backend
  const refreshKpis = async () => {
    try {
      const response = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: 'show kpi dashboard',
          session_id: sessionId,
        }),
      });
      await response.json();
    } catch (e) {
      console.error("Failed to refresh live KPIs:", e);
    }
  };

  useEffect(() => {
    refreshKpis();
  }, []);

  // Handle message send
  const handleSend = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!chatInput.trim() && !attachedFile) return;

    let fullMessage = chatInput;
    let displayMessage = chatInput;

    if (attachedFile) {
      fullMessage = `Read the file at "${attachedFile.path}" and answer: ${chatInput || 'summarise this document'}`;
      displayMessage = `[Attached: ${attachedFile.name}] ${chatInput || 'Summarise this document'}`;
    }

    const userMsg: Message = {
      id: Math.random().toString(),
      sender: 'user',
      text: displayMessage,
    };

    setMessages(prev => [...prev, userMsg]);
    setChatInput('');
    setAttachedFile(null);
    setIsTyping(true);

    try {
      const response = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: fullMessage,
          session_id: sessionId,
        }),
      });
      const data = await response.json();

      const assistantMsg: Message = {
        id: Math.random().toString(),
        sender: 'assistant',
        text: data.reply,
      };
      setMessages(prev => [...prev, assistantMsg]);

      if (data.reply.includes('Saved to:')) {
        const pathMatch = data.reply.match(/Saved to:\s*([^\n]+)/);
        if (pathMatch) {
          const fullPath = pathMatch[1].trim();
          const name = fullPath.replace(/\\/g, '/').split('/').pop() || 'report.pdf';
          const type = name.endsWith('.pptx') ? 'pptx' : 'pdf';
          const newDoc: Doc = {
            id: Math.random().toString(),
            name,
            path: fullPath,
            type,
            timestamp: new Date().toLocaleTimeString(),
          };
          setDocuments(prev => [newDoc, ...prev]);
        }
      }
    } catch (error) {
      setMessages(prev => [...prev, {
        id: Math.random().toString(),
        sender: 'assistant',
        text: "Unable to connect to the backend server. Make sure FastAPI is running on http://localhost:8000.",
      }]);
    } finally {
      setIsTyping(false);
    }
  };

  // Handle file attachment upload
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('http://localhost:8000/upload', {
        method: 'POST',
        body: formData,
      });
      const data = await response.json();

      if (response.ok) {
        setAttachedFile({
          name: file.name,
          path: data.filepath,
          type: file.name.endsWith('.pptx') ? 'pptx' : 'pdf',
        });
        const newDoc: Doc = {
          id: Math.random().toString(),
          name: file.name,
          path: data.filepath,
          type: file.name.endsWith('.pptx') ? 'pptx' : 'pdf',
          timestamp: new Date().toLocaleTimeString(),
        };
        setDocuments(prev => [newDoc, ...prev]);
      } else {
        alert(data.detail || "Upload failed");
      }
    } catch (err) {
      alert("Error contacting the file upload server.");
    } finally {
      setIsUploading(false);
    }
  };

  // Generate Report Helper (Fast Trigger Buttons)
  const triggerReport = async (type: 'pdf' | 'pptx') => {
    setIsTyping(true);
    setActiveTab('chat');
    
    const userMsg = `generate a kpi ${type}`;
    setMessages(prev => [...prev, {
      id: Math.random().toString(),
      sender: 'user',
      text: `Generate styled ${type.toUpperCase()} report`,
    }]);

    try {
      const response = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userMsg,
          session_id: sessionId,
        }),
      });
      const data = await response.json();
      setMessages(prev => [...prev, {
        id: Math.random().toString(),
        sender: 'assistant',
        text: data.reply,
      }]);

      const pathMatch = data.reply.match(/Saved to:\s*([^\n]+)/);
      if (pathMatch) {
        const fullPath = pathMatch[1].trim();
        const name = fullPath.replace(/\\/g, '/').split('/').pop() || `report.${type}`;
        setDocuments(prev => [{
          id: Math.random().toString(),
          name,
          path: fullPath,
          type,
          timestamp: new Date().toLocaleTimeString(),
        }, ...prev]);
      }
    } catch (e) {
      alert("Failed to generate report.");
    } finally {
      setIsTyping(false);
    }
  };

  // Format assistant replies containing tables/lists into markdown-like JSX
  const renderMessageContent = (text: string) => {
    if (text.includes('|')) {
      const lines = text.split('\n');
      const tableLines = lines.filter(l => l.includes('|'));
      const tableIndex = lines.indexOf(tableLines[0]);
      
      if (tableIndex !== -1) {
        const preTable = lines.slice(0, tableIndex).join('\n');
        const postTable = lines.slice(tableIndex + tableLines.length).join('\n');
        
        const rows = tableLines.map(row => row.split('|').map(cell => cell.trim()).filter(Boolean));
        const headers = rows[0];
        const dataRows = rows.slice(2);

        return (
          <div className="space-y-2">
            {preTable.trim() && <p className="whitespace-pre-wrap text-xs text-zinc-300 leading-normal tracking-tight">{preTable}</p>}
            <div className="overflow-x-auto border border-white/[0.03] rounded">
              <table className="w-full text-left border-collapse text-[10px]">
                <thead>
                  <tr className="bg-white/[0.01] border-b border-white/[0.03]">
                    {headers.map((h, i) => (
                      <th key={i} className="px-2 py-1 font-semibold text-zinc-200 border-r border-white/[0.03] last:border-r-0">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {dataRows.map((row, i) => (
                    <tr key={i} className="border-b border-white/[0.03] last:border-b-0 hover:bg-white/[0.01] transition-colors duration-150">
                      {row.map((cell, ci) => (
                        <td key={ci} className="px-2 py-1 text-zinc-400 border-r border-white/[0.03] last:border-r-0 font-mono">{cell}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {postTable.trim() && <p className="whitespace-pre-wrap text-xs text-zinc-400 leading-normal tracking-tight">{postTable}</p>}
          </div>
        );
      }
    }

    return <p className="whitespace-pre-wrap text-xs text-zinc-300 leading-relaxed tracking-tight">{text}</p>;
  };

  return (
    <div className="flex h-screen w-screen bg-canvas text-xs antialiased tracking-tight relative overflow-hidden font-sans">
      
      {/* Ambient background glow */}
      <div className="absolute top-0 right-0 w-[400px] h-[400px] bg-indigo-500/5 blur-[120px] pointer-events-none z-0" />
      
      {/* Sidebar Navigation */}
      <aside className="w-[200px] bg-surface border-r border-white/[0.03] flex flex-col p-2 z-10 relative">
        <div className="flex items-center gap-1.5 p-1 mb-4">
          <div className="w-4 h-4 rounded bg-indigo-500/15 flex items-center justify-center border border-indigo-500/30">
            <svg className="w-2.5 h-2.5 text-indigo-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polygon points="12 2 2 7 12 12 22 7 12 2" />
              <polyline points="2 17 12 22 22 17" />
              <polyline points="2 12 12 17 22 12" />
            </svg>
          </div>
          <span className="text-sm font-semibold tracking-tight text-zinc-100">LAWMIS Panel</span>
        </div>
        
        <nav className="flex flex-col gap-1">
          <button 
            className={`w-full text-left font-medium tracking-tight rounded px-2 py-1.5 flex items-center gap-2 border transition-all duration-300 outline-none ${
              activeTab === 'chat' 
                ? 'bg-indigo-500/10 border-indigo-500/20 text-indigo-400' 
                : 'bg-transparent border-transparent text-zinc-400 hover:bg-white/[0.02] hover:text-zinc-200 active:bg-white/[0.04]'
            }`}
            onClick={() => setActiveTab('chat')}
          >
            <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            </svg>
            <span>Chat Assistant</span>
          </button>
          
          <button 
            className={`w-full text-left font-medium tracking-tight rounded px-2 py-1.5 flex items-center gap-2 border transition-all duration-300 outline-none ${
              activeTab === 'dashboard' 
                ? 'bg-indigo-500/10 border-indigo-500/20 text-indigo-400' 
                : 'bg-transparent border-transparent text-zinc-400 hover:bg-white/[0.02] hover:text-zinc-200 active:bg-white/[0.04]'
            }`}
            onClick={() => setActiveTab('dashboard')}
          >
            <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="20" x2="18" y2="10" />
              <line x1="12" y1="20" x2="12" y2="4" />
              <line x1="6" y1="20" x2="6" y2="14" />
            </svg>
            <span>KPI Dashboard</span>
          </button>
          
          <button 
            className={`w-full text-left font-medium tracking-tight rounded px-2 py-1.5 flex items-center gap-2 border transition-all duration-300 outline-none ${
              activeTab === 'documents' 
                ? 'bg-indigo-500/10 border-indigo-500/20 text-indigo-400' 
                : 'bg-transparent border-transparent text-zinc-400 hover:bg-white/[0.02] hover:text-zinc-200 active:bg-white/[0.04]'
            }`}
            onClick={() => setActiveTab('documents')}
          >
            <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
              <line x1="16" y1="13" x2="8" y2="13" />
              <line x1="16" y1="17" x2="8" y2="17" />
            </svg>
            <span>Reports & Docs</span>
          </button>
        </nav>

        <div className="mt-auto border-t border-white/[0.03] pt-2">
          <div className="flex items-center gap-1.5 p-1 text-[10px] text-zinc-500 font-mono">
            <span className="w-1.5 h-1.5 bg-indigo-500 rounded-full shadow-[0_0_8px_rgba(99,102,241,0.5)]"></span>
            <span>API Active</span>
          </div>
        </div>
      </aside>

      {/* Main Panel Content */}
      <main className="flex-1 flex flex-col h-screen relative z-10 overflow-hidden">
        
        {/* Top Header */}
        <header className="h-[40px] border-b border-white/[0.03] bg-surface/50 backdrop-blur-md px-3 flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <span className="text-sm font-semibold text-zinc-100">
              {activeTab === 'chat' && 'Assistant Intelligence'}
              {activeTab === 'dashboard' && 'KPI Dashboard'}
              {activeTab === 'documents' && 'Document Center'}
            </span>
          </div>
          
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-mono text-zinc-500 px-1.5 py-0.5 rounded bg-white/[0.02] border border-white/[0.03]">
              http://localhost:8000
            </span>
          </div>
        </header>

        {/* Dynamic Panels */}
        <section className="flex-1 overflow-y-auto p-2">
          
          {/* TAB 1: CHAT PANEL */}
          {activeTab === 'chat' && (
            <div className="flex flex-col h-full max-w-[800px] mx-auto w-full">
              <div className="flex-1 overflow-y-auto space-y-2 pr-1 pb-4">
                {messages.map(msg => (
                  <div key={msg.id} className={`flex w-full ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-[75%] rounded px-2.5 py-2 transition-all duration-300 ${
                      msg.sender === 'user'
                        ? 'bg-indigo-500/10 border border-indigo-500/20 text-zinc-100 rounded-br-none'
                        : 'bg-[#090d16] border border-white/[0.03] text-zinc-300 rounded-bl-none shadow-glow hover:border-white/[0.08]'
                    }`}>
                      {renderMessageContent(msg.text)}
                    </div>
                  </div>
                ))}
                
                {isTyping && (
                  <div className="flex w-full justify-start">
                    <div className="bg-[#090d16] border border-white/[0.03] rounded rounded-bl-none px-3 py-2 flex items-center gap-1">
                      <span className="w-1.5 h-1.5 bg-indigo-500/40 rounded-full animate-pulse"></span>
                      <span className="w-1.5 h-1.5 bg-indigo-500/60 rounded-full animate-pulse delay-75"></span>
                      <span className="w-1.5 h-1.5 bg-indigo-500/80 rounded-full animate-pulse delay-150"></span>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>

              {/* Chat Send Form */}
              <div className="border-t border-white/[0.03] pt-2">
                {attachedFile && (
                  <div className="flex items-center justify-between bg-indigo-500/10 border border-indigo-500/20 px-2 py-1 rounded mb-2 text-xs text-indigo-400">
                    <div className="flex items-center gap-1.5 font-mono text-[10px]">
                      <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
                      </svg>
                      <span>Ready to query: {attachedFile.name}</span>
                    </div>
                    <button 
                      type="button" 
                      onClick={() => setAttachedFile(null)} 
                      className="text-red-400 hover:text-red-300 font-medium text-[10px] flex items-center gap-1 cursor-pointer outline-none bg-transparent border-none"
                    >
                      <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                        <polyline points="3 6 5 6 21 6" />
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                      </svg>
                      <span>Remove</span>
                    </button>
                  </div>
                )}

                <form onSubmit={handleSend} className="flex items-center gap-1.5 bg-[#090d16] border border-white/[0.03] rounded p-1 transition-all duration-300 focus-within:border-indigo-500/30 focus-within:shadow-[0_0_15px_-3px_rgba(99,102,241,0.2)]">
                  <input 
                    type="file"
                    ref={fileInputRef}
                    className="hidden"
                    accept=".pdf,.pptx"
                    onChange={handleFileUpload}
                  />
                  <button 
                    type="button" 
                    className="bg-white/[0.02] border border-white/[0.03] text-zinc-400 w-7 h-7 rounded hover:bg-white/[0.04] hover:border-white/[0.08] hover:text-zinc-200 active:bg-indigo-500/10 active:border-indigo-500/20 active:text-indigo-400 flex items-center justify-center transition-all duration-300 disabled:opacity-40 disabled:cursor-not-allowed outline-none"
                    onClick={() => fileInputRef.current?.click()}
                    disabled={isUploading}
                  >
                    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
                    </svg>
                  </button>
                  <input 
                    type="text" 
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    placeholder={attachedFile ? "Query attached document details..." : "Query workshops, payment logs, generate reports..."}
                    className="flex-1 bg-transparent border-none text-zinc-100 text-xs py-1.5 px-1 outline-none placeholder:text-zinc-500"
                    disabled={isTyping || isUploading}
                  />
                  <button 
                    type="submit" 
                    className="bg-indigo-500 border border-indigo-600 text-white w-7 h-7 rounded hover:bg-indigo-400 hover:border-indigo-500 active:bg-indigo-600 active:border-indigo-700 flex items-center justify-center transition-all duration-300 disabled:opacity-40 disabled:cursor-not-allowed outline-none"
                    disabled={isTyping || isUploading || (!chatInput.trim() && !attachedFile)}
                  >
                    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                      <line x1="22" y1="2" x2="11" y2="13" />
                      <polygon points="22 2 15 22 11 13 2 9 22 2" />
                    </svg>
                  </button>
                </form>
              </div>
            </div>
          )}

          {/* TAB 2: KPI DASHBOARD */}
          {activeTab === 'dashboard' && (
            <div className="max-w-[1000px] mx-auto w-full space-y-2">
              
              {/* Export Triggers Group */}
              <div className="flex gap-2">
                <button 
                  onClick={() => triggerReport('pdf')}
                  className="bg-white/[0.02] border border-white/[0.03] text-zinc-300 px-3 py-1.5 rounded hover:bg-white/[0.04] hover:border-white/[0.08] hover:text-zinc-100 active:bg-indigo-500/10 active:border-indigo-500/20 active:text-indigo-400 flex items-center gap-1.5 transition-all duration-300 outline-none group text-xs font-medium"
                >
                  <svg className="w-3.5 h-3.5 text-zinc-400 group-hover:text-zinc-200" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                    <polyline points="14 2 14 8 20 8" />
                  </svg>
                  <span>Export Report to PDF</span>
                  <svg className="w-3 h-3 text-zinc-500 transform transition-transform group-hover:translate-x-[0.5px]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="9 18 15 12 9 6" />
                  </svg>
                </button>
                
                <button 
                  onClick={() => triggerReport('pptx')}
                  className="bg-white/[0.02] border border-white/[0.03] text-zinc-300 px-3 py-1.5 rounded hover:bg-white/[0.04] hover:border-white/[0.08] hover:text-zinc-100 active:bg-indigo-500/10 active:border-indigo-500/20 active:text-indigo-400 flex items-center gap-1.5 transition-all duration-300 outline-none group text-xs font-medium"
                >
                  <svg className="w-3.5 h-3.5 text-zinc-400 group-hover:text-zinc-200" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                    <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
                  </svg>
                  <span>Export Deck to PowerPoint</span>
                  <svg className="w-3 h-3 text-zinc-500 transform transition-transform group-hover:translate-x-[0.5px]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="9 18 15 12 9 6" />
                  </svg>
                </button>
              </div>

              {/* Bento KPI grid */}
              <div className="grid grid-cols-3 gap-2">
                
                {/* Metric 1 */}
                <div className="bg-[#090d16] border border-white/[0.03] rounded p-2.5 relative overflow-hidden shadow-glow hover:border-white/[0.08] transition-all duration-300 flex flex-col justify-between">
                  <div>
                    <div className="text-[10px] text-zinc-400 font-semibold tracking-tight uppercase flex items-center justify-between mb-1">
                      <span>Workshops</span>
                      <svg className="w-3.5 h-3.5 text-indigo-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                        <rect x="4" y="2" width="16" height="20" rx="2" ry="2" />
                        <line x1="9" y1="22" x2="9" y2="16" />
                        <line x1="15" y1="22" x2="15" y2="16" />
                      </svg>
                    </div>
                    <span className="text-xl font-bold tracking-tight text-zinc-100">{kpi.workshops.total}</span>
                  </div>
                  <div className="mt-3 border-t border-white/[0.02] pt-2 flex flex-col gap-1">
                    <div className="flex justify-between text-[10px]">
                      <span className="text-zinc-500">Active (Approved)</span>
                      <span className="text-indigo-400 font-semibold">{kpi.workshops.active}</span>
                    </div>
                    <div className="flex justify-between text-[10px]">
                      <span className="text-zinc-500">Pending Review</span>
                      <span className="text-zinc-300 font-semibold">{kpi.workshops.pending}</span>
                    </div>
                  </div>
                </div>

                {/* Metric 2 */}
                <div className="bg-[#090d16] border border-white/[0.03] rounded p-2.5 relative overflow-hidden shadow-glow hover:border-white/[0.08] transition-all duration-300 flex flex-col justify-between">
                  <div>
                    <div className="text-[10px] text-zinc-400 font-semibold tracking-tight uppercase flex items-center justify-between mb-1">
                      <span>Licenses</span>
                      <svg className="w-3.5 h-3.5 text-indigo-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
                        <polyline points="14 2 14 8 20 8" />
                      </svg>
                    </div>
                    <span className="text-xl font-bold tracking-tight text-zinc-100">{kpi.licenses.total}</span>
                  </div>
                  <div className="mt-3 border-t border-white/[0.02] pt-2 flex flex-col gap-1">
                    <div className="flex justify-between text-[10px]">
                      <span className="text-zinc-500">Active Licenses</span>
                      <span className="text-indigo-400 font-semibold">{kpi.licenses.active}</span>
                    </div>
                    <div className="flex justify-between text-[10px]">
                      <span className="text-zinc-500">Expired</span>
                      <span className="text-red-400 font-semibold">{kpi.licenses.expired}</span>
                    </div>
                  </div>
                </div>

                {/* Metric 3 */}
                <div className="bg-[#090d16] border border-white/[0.03] rounded p-2.5 relative overflow-hidden shadow-glow hover:border-white/[0.08] transition-all duration-300 flex flex-col justify-between">
                  <div>
                    <div className="text-[10px] text-zinc-400 font-semibold tracking-tight uppercase flex items-center justify-between mb-1">
                      <span>Payments & Revenue</span>
                      <svg className="w-3.5 h-3.5 text-indigo-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                        <rect x="1" y="4" width="22" height="16" rx="2" ry="2" />
                        <line x1="1" y1="10" x2="23" y2="10" />
                      </svg>
                    </div>
                    <span className="text-xl font-bold tracking-tight text-zinc-100">PKR {kpi.payments.total_revenue}</span>
                  </div>
                  <div className="mt-3 border-t border-white/[0.02] pt-2 flex flex-col gap-1">
                    <div className="flex justify-between text-[10px]">
                      <span className="text-zinc-500">Paid Challans</span>
                      <span className="text-zinc-300 font-semibold">{kpi.payments.paid_count}</span>
                    </div>
                    <div className="flex justify-between text-[10px]">
                      <span className="text-zinc-500">Pending Payments</span>
                      <span className="text-zinc-300 font-semibold">{kpi.payments.pending_count}</span>
                    </div>
                  </div>
                </div>

              </div>

              {/* Bento details row */}
              <div className="grid grid-cols-2 gap-2">
                
                {/* Cities table */}
                <div className="bg-[#090d16] border border-white/[0.03] rounded p-3 shadow-glow hover:border-white/[0.08] transition-all duration-300">
                  <div className="text-xs font-semibold text-zinc-100 mb-2 flex items-center gap-1.5">
                    <span>Top Workshop Cities</span>
                  </div>
                  <table className="w-full text-left border-collapse text-[10px]">
                    <thead>
                      <tr className="border-b border-white/[0.03]">
                        <th className="py-1 font-semibold text-zinc-400">City</th>
                        <th className="py-1 font-semibold text-zinc-400 text-right">Workshops Count</th>
                      </tr>
                    </thead>
                    <tbody>
                      {kpi.cities.map((c: any, i: number) => (
                        <tr key={i} className="border-b border-white/[0.02] last:border-b-0">
                          <td className="py-1.5 text-zinc-300">{c.city}</td>
                          <td className="py-1.5 text-zinc-100 font-semibold text-right font-mono">{c.count}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* DB System Status Table */}
                <div className="bg-[#090d16] border border-white/[0.03] rounded p-3 shadow-glow hover:border-white/[0.08] transition-all duration-300">
                  <div className="text-xs font-semibold text-zinc-100 mb-2 flex items-center gap-1.5">
                    <span>Database Safety Status</span>
                  </div>
                  <table className="w-full text-left border-collapse text-[10px]">
                    <tbody>
                      <tr className="border-b border-white/[0.02]">
                        <td className="py-2 text-zinc-400">SELECT-only Enforcement</td>
                        <td className="py-2 text-right">
                          <span className="inline-flex items-center ring-1 ring-inset bg-indigo-500/10 text-indigo-400 ring-indigo-500/20 text-[9px] font-semibold px-1 py-0.5 rounded">
                            READ ONLY
                          </span>
                        </td>
                      </tr>
                      <tr className="border-b border-white/[0.02]">
                        <td className="py-2 text-zinc-400">PostgreSQL Connection</td>
                        <td className="py-2 text-right text-zinc-100 font-mono font-semibold">Active (5433)</td>
                      </tr>
                      <tr className="border-b border-white/[0.02] last:border-b-0">
                        <td className="py-2 text-zinc-400">SQL Injection Sandbox</td>
                        <td className="py-2 text-right text-emerald-400 font-semibold">SECURED</td>
                      </tr>
                    </tbody>
                  </table>
                </div>

              </div>

            </div>
          )}

          {/* TAB 3: DOCUMENTS PANEL */}
          {activeTab === 'documents' && (
            <div className="max-w-[800px] mx-auto w-full space-y-3">
              
              {/* File Dropzone */}
              <div 
                className="border border-dashed border-white/[0.1] bg-white/[0.01] hover:bg-white/[0.02] hover:border-indigo-500/40 rounded p-4 text-center cursor-pointer transition-all duration-300 flex flex-col items-center gap-1.5"
                onClick={() => fileInputRef.current?.click()}
              >
                <svg className="w-6 h-6 text-zinc-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21.2 15c.9-1 1.3-2.4.9-3.7-.4-1.3-1.4-2.2-2.7-2.3H18c-.8-3.2-3.8-5.3-7-4.5-2.5.6-4.5 2.5-5.1 5-.2 0-.4-.1-.6-.1C2.4 9.4 0 11.8 0 14.7c0 2.8 2.2 5 5 5h13c2.2 0 4-1.8 4-4.7z" />
                  <polyline points="16 12 12 8 8 12" />
                  <line x1="12" y1="8" x2="12" y2="18" />
                </svg>
                <span className="text-xs font-semibold text-zinc-200">Upload PDF / PPTX for Document Q&amp;A</span>
                <span className="text-[10px] text-zinc-500 font-mono">Drag &amp; drop or click to upload</span>
              </div>

              {/* Document Registry list */}
              <div className="space-y-1.5">
                <span className="text-xs font-semibold text-zinc-100 block mb-1">Document Registry</span>
                
                {documents.length === 0 ? (
                  <div className="bg-[#090d16] border border-white/[0.03] rounded p-4 text-center text-zinc-500">
                    No documents uploaded or exported reports found.
                  </div>
                ) : (
                  documents.map(doc => (
                    <div key={doc.id} className="bg-[#090d16] border border-white/[0.03] rounded p-2.5 flex items-center justify-between hover:border-white/[0.08] transition-all duration-300">
                      <div className="flex items-center gap-2">
                        <div className="w-7 h-7 rounded bg-white/[0.02] border border-white/[0.03] flex items-center justify-center text-zinc-400">
                          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                            <polyline points="14 2 14 8 20 8" />
                          </svg>
                        </div>
                        <div>
                          <p className="text-xs font-medium text-zinc-200">{doc.name}</p>
                          <p className="text-[10px] text-zinc-500 font-mono">{doc.type.toUpperCase()} • Generated {doc.timestamp}</p>
                        </div>
                      </div>
                      
                      <button 
                        onClick={() => {
                          setAttachedFile({ name: doc.name, path: doc.path, type: doc.type });
                          setActiveTab('chat');
                        }}
                        className="text-[10px] font-medium px-2 py-1 rounded border border-white/[0.03] bg-white/[0.01] hover:bg-white/[0.03] hover:border-white/[0.08] active:bg-indigo-500/10 active:border-indigo-500/20 active:text-indigo-400 transition-all duration-300 outline-none"
                      >
                        Ask Document
                      </button>
                    </div>
                  ))
                )}
              </div>

            </div>
          )}

        </section>
      </main>
    </div>
  );
}
