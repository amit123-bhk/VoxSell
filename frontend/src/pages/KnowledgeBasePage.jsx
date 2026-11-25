import React, { useState, useEffect } from 'react';
import { UploadCloud, RefreshCw } from 'lucide-react';

export default function KnowledgeBasePage() {
  const [unanswered, setUnanswered] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploadCategory, setUploadCategory] = useState('pricing');
  const [uploadStatus, setUploadStatus] = useState(null);
  const [isUploading, setIsUploading] = useState(false);

  // Existing Knowledge Documents
  const indexedDocs = [
    { name: 'pricing.md', category: 'Pricing & Tiers', chunks: 14, status: 'INDEXED' },
    { name: 'product_catalogue.md', category: 'Product Features', chunks: 28, status: 'INDEXED' },
    { name: 'faqs.md', category: 'General FAQs', chunks: 20, status: 'INDEXED' },
  ];

  useEffect(() => {
    fetchUnansweredQuestions();
  }, []);

  const fetchUnansweredQuestions = async () => {
    try {
      const res = await fetch('/analytics/unanswered-questions');
      const data = await res.json();
      if (data.status === 'success') {
        setUnanswered(data.data || []);
      }
    } catch (e) {
      console.error('Error fetching unanswered questions:', e);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setIsUploading(true);
    setUploadStatus(null);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('category', uploadCategory);

    try {
      const res = await fetch('/kb/upload', {
        method: 'POST',
        body: formData,
      });

      const data = await res.json();
      if (res.ok) {
        setUploadStatus({
          type: 'success',
          message: `Ingested "${file.name}". Hot-reloaded ${data.chunks_indexed || 'multiple'} chunks into ChromaDB index.`,
        });
      } else {
        throw new Error(data.detail || 'Upload ingestion failed.');
      }
    } catch (err) {
      setUploadStatus({
        type: 'error',
        message: err.message || 'File upload failed.',
      });
    } finally {
      setIsUploading(false);
      e.target.value = '';
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6 font-mono">
      {/* Header */}
      <div>
        <h1 className="text-sm font-bold text-white uppercase tracking-wider">
          DOCUMENT INDEX & KNOWLEDGE GAP CURATION
        </h1>
        <p className="text-xs text-zinc-400 mt-0.5">
          Ingest enterprise product documentation into ChromaDB and resolve anti-hallucination queries.
        </p>
      </div>

      {/* Upload Dropzone & Indexed Docs Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Document Ingestion Card */}
        <div className="p-4 bg-zinc-950 border border-zinc-800 rounded space-y-4">
          <div>
            <h2 className="text-xs font-bold text-white uppercase">
              DOCUMENT INGESTION (HOT RELOAD)
            </h2>
            <p className="text-xs text-zinc-400 mt-0.5 font-sans">
              PDF, DOCX, Markdown, Text, CSV. Immediate chunking and embedding.
            </p>
          </div>

          <div className="space-y-3">
            <div>
              <label className="block text-[10px] uppercase text-zinc-400 mb-1">Target Category</label>
              <select
                value={uploadCategory}
                onChange={(e) => setUploadCategory(e.target.value)}
                className="w-full px-3 py-1.5 bg-zinc-900 border border-zinc-800 rounded text-xs text-white focus:outline-none focus:border-zinc-600"
              >
                <option value="pricing">Pricing & Commercial Terms</option>
                <option value="product">Product Specs & Features</option>
                <option value="enterprise">Security, SOC2 & Compliance</option>
                <option value="faqs">Company Policies & FAQs</option>
              </select>
            </div>

            <div className="border border-dashed border-zinc-800 hover:border-zinc-600 rounded p-6 text-center cursor-pointer bg-zinc-900/50 relative">
              <input
                type="file"
                onChange={handleFileUpload}
                accept=".pdf,.docx,.txt,.md,.csv"
                className="absolute inset-0 opacity-0 cursor-pointer w-full h-full"
              />
              <UploadCloud className="h-6 w-6 text-zinc-400 mx-auto mb-2" />
              <span className="text-xs text-white block">
                {isUploading ? 'INDEXING CHUNKS...' : 'SELECT DOCUMENT TO INGEST'}
              </span>
              <span className="text-[10px] text-zinc-500 block mt-1">
                MAX 10MB | CHUNK SIZE 500 TOKENS (50-TOKEN OVERLAP)
              </span>
            </div>

            {uploadStatus && (
              <div
                className={`p-2.5 rounded text-xs border ${
                  uploadStatus.type === 'success'
                    ? 'bg-zinc-900 border-green-800 text-green-400'
                    : 'bg-zinc-900 border-red-800 text-red-400'
                }`}
              >
                {uploadStatus.message}
              </div>
            )}
          </div>
        </div>

        {/* Currently Indexed Documents */}
        <div className="p-4 bg-zinc-950 border border-zinc-800 rounded space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-bold text-white uppercase">
              ACTIVE COLLECTIONS
            </h2>
            <span className="text-[10px] text-white bg-zinc-900 px-2 py-0.5 rounded border border-zinc-800">
              CHROMADB ACTIVE
            </span>
          </div>

          <div className="space-y-2">
            {indexedDocs.map((doc, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between p-3 bg-zinc-900 border border-zinc-800 rounded text-xs"
              >
                <div>
                  <span className="font-bold text-white block">{doc.name}</span>
                  <span className="text-[10px] text-zinc-400 font-sans">{doc.category}</span>
                </div>
                <div className="text-right">
                  <span className="text-zinc-300 block">{doc.chunks} chunks</span>
                  <span className="text-[10px] text-zinc-500">{doc.status}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Unanswered Questions Catalog */}
      <div className="p-4 bg-zinc-950 border border-zinc-800 rounded space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xs font-bold text-white uppercase">
              UNANSWERED QUERIES (ANTI-HALLUCINATION FALLBACKS)
            </h2>
            <p className="text-xs text-zinc-400 mt-0.5 font-sans">
              Customer queries where agent triggered confirmation fallback.
            </p>
          </div>
          <button
            onClick={fetchUnansweredQuestions}
            className="p-1.5 rounded bg-zinc-900 hover:bg-zinc-800 text-zinc-300 text-xs flex items-center gap-1 border border-zinc-800"
          >
            <RefreshCw className="h-3 w-3" />
            REFRESH
          </button>
        </div>

        <div className="divide-y divide-zinc-900">
          {loading ? (
            <div className="py-6 text-center text-xs text-zinc-500">Querying backlog...</div>
          ) : unanswered.length === 0 ? (
            <div className="py-6 text-center text-xs text-zinc-500">
              No unanswered queries recorded.
            </div>
          ) : (
            unanswered.map((q, idx) => (
              <div key={idx} className="py-2.5 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-white font-sans">"{q.question}"</span>
                    <span className="px-1.5 py-0.5 rounded bg-zinc-900 text-zinc-400 border border-zinc-800 text-[10px]">
                      {q.frequency}x
                    </span>
                  </div>
                  <div className="text-[10px] text-zinc-500 font-sans">
                    Category: {q.category}
                  </div>
                </div>

                <div>
                  <span className="text-[10px] text-zinc-400 px-2 py-0.5 rounded bg-zinc-900 border border-zinc-800">
                    {q.status}
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
