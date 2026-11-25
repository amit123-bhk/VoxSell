import React, { useState, useEffect } from 'react';
import { Search, X } from 'lucide-react';

export default function LeadsPage({ token }) {
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterClass, setFilterClass] = useState('ALL');
  const [selectedLead, setSelectedLead] = useState(null);

  useEffect(() => {
    fetchLeads();
  }, [filterClass]);

  const fetchLeads = async () => {
    setLoading(true);
    try {
      const url = filterClass === 'ALL' ? '/leads' : `/leads?classification=${filterClass}`;
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      const res = await fetch(url, { headers });
      const data = await res.json();
      if (data.status === 'success') {
        setLeads(data.data || []);
      }
    } catch (e) {
      console.error('Error fetching leads:', e);
    } finally {
      setLoading(false);
    }
  };

  const filteredLeads = leads.filter((l) => {
    const q = searchTerm.toLowerCase();
    return (
      (l.name || '').toLowerCase().includes(q) ||
      (l.company || '').toLowerCase().includes(q) ||
      (l.phone_number || '').includes(q)
    );
  });

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      {/* Header & Controls */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-sm font-bold text-white font-mono uppercase tracking-wider">
            LEAD PIPELINE RECORDS
          </h1>
          <p className="text-xs font-mono text-zinc-400 mt-0.5">
            Real-time pipeline qualified by BANT criteria and speech sentiment.
          </p>
        </div>

        {/* Filter & Search */}
        <div className="flex flex-wrap items-center gap-2 w-full sm:w-auto font-mono">
          <div className="relative flex-1 sm:w-64">
            <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-zinc-500" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Filter by name, company, phone..."
              className="w-full pl-8 pr-3 py-1.5 bg-zinc-900 border border-zinc-800 rounded text-xs text-white focus:outline-none focus:border-zinc-600"
            />
          </div>

          <div className="flex items-center gap-1 bg-zinc-900 border border-zinc-800 rounded p-0.5 text-xs">
            {['ALL', 'HOT', 'WARM', 'COLD'].map((f) => (
              <button
                key={f}
                onClick={() => setFilterClass(f)}
                className={`px-2.5 py-1 rounded font-medium ${
                  filterClass === f
                    ? 'bg-zinc-800 text-white border border-zinc-700'
                    : 'text-zinc-400 hover:text-white'
                }`}
              >
                {f}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Leads Table */}
      <div className="bg-zinc-950 border border-zinc-800 rounded overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-zinc-900 border-b border-zinc-800 text-zinc-400 uppercase font-semibold">
              <tr>
                <th className="py-3 px-4">PROSPECT / COMPANY</th>
                <th className="py-3 px-4">PHONE</th>
                <th className="py-3 px-4">BANT SCORE</th>
                <th className="py-3 px-4">STATUS</th>
                <th className="py-3 px-4">LANG</th>
                <th className="py-3 px-4">LAST CALL</th>
                <th className="py-3 px-4">APPOINTMENT</th>
                <th className="py-3 px-4 text-right">ACTION</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-900 text-zinc-300">
              {loading ? (
                <tr>
                  <td colSpan="8" className="text-center py-10 text-zinc-500">
                    Loading records...
                  </td>
                </tr>
              ) : filteredLeads.length === 0 ? (
                <tr>
                  <td colSpan="8" className="text-center py-10 text-zinc-500">
                    No lead records matching search parameters.
                  </td>
                </tr>
              ) : (
                filteredLeads.map((lead) => (
                  <tr
                    key={lead.id}
                    onClick={() => setSelectedLead(lead)}
                    className="hover:bg-zinc-900 cursor-pointer"
                  >
                    <td className="py-3 px-4 font-sans">
                      <div className="font-semibold text-white">{lead.name}</div>
                      <div className="text-[11px] text-zinc-400">{lead.company}</div>
                    </td>
                    <td className="py-3 px-4 text-zinc-400">{lead.phone_number}</td>
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-white">{lead.lead_score}</span>
                        <div className="w-16 bg-zinc-900 h-1.5 rounded overflow-hidden border border-zinc-800">
                          <div
                            className="h-full bg-white"
                            style={{ width: `${lead.lead_score}%` }}
                          />
                        </div>
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold border border-zinc-800 bg-zinc-900 text-white">
                        {lead.classification}
                      </span>
                    </td>
                    <td className="py-3 px-4 uppercase text-[11px] text-zinc-400">
                      {lead.language}
                    </td>
                    <td className="py-3 px-4 text-zinc-400 text-[11px]">
                      {lead.last_call_at ? new Date(lead.last_call_at).toLocaleDateString() : 'N/A'}
                    </td>
                    <td className="py-3 px-4 text-zinc-400 text-[11px]">
                      {lead.next_appointment ? new Date(lead.next_appointment).toLocaleDateString() : 'NONE'}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedLead(lead);
                        }}
                        className="px-2.5 py-1 rounded bg-zinc-900 hover:bg-zinc-800 text-zinc-300 hover:text-white border border-zinc-800 text-[11px]"
                      >
                        VIEW
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Lead Detail Inspection Modal */}
      {selectedLead && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/90">
          <div className="w-full max-w-2xl bg-zinc-950 border border-zinc-800 rounded p-6 max-h-[90vh] overflow-y-auto space-y-5 font-mono shadow-2xl">
            <div className="flex items-start justify-between border-b border-zinc-800 pb-3">
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-sm font-bold text-white uppercase">{selectedLead.name}</h2>
                  <span className="px-2 py-0.5 rounded text-xs border border-zinc-800 bg-zinc-900 text-white">
                    {selectedLead.classification} [{selectedLead.lead_score}/100]
                  </span>
                </div>
                <p className="text-xs text-zinc-400 mt-1">
                  COMPANY: {selectedLead.company} | PHONE: {selectedLead.phone_number}
                </p>
              </div>
              <button
                onClick={() => setSelectedLead(null)}
                className="p-1 rounded text-zinc-400 hover:text-white hover:bg-zinc-900"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {/* BANT Parameters */}
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="p-2.5 bg-zinc-900 rounded border border-zinc-800">
                <span className="text-zinc-500 block uppercase text-[10px]">Budget</span>
                <span className="text-white font-medium">{selectedLead.bant?.budget || 'Not specified'}</span>
              </div>
              <div className="p-2.5 bg-zinc-900 rounded border border-zinc-800">
                <span className="text-zinc-500 block uppercase text-[10px]">Authority</span>
                <span className="text-white font-medium">{selectedLead.bant?.authority || 'Not specified'}</span>
              </div>
              <div className="p-2.5 bg-zinc-900 rounded border border-zinc-800">
                <span className="text-zinc-500 block uppercase text-[10px]">Identified Need</span>
                <span className="text-white font-medium">{selectedLead.bant?.need || 'Not specified'}</span>
              </div>
              <div className="p-2.5 bg-zinc-900 rounded border border-zinc-800">
                <span className="text-zinc-500 block uppercase text-[10px]">Timeline</span>
                <span className="text-white font-medium">{selectedLead.bant?.timeline || 'Not specified'}</span>
              </div>
            </div>

            {/* Past Calls Timeline */}
            <div>
              <h3 className="text-xs font-bold text-zinc-400 uppercase mb-3">
                CALL AUDIT & DIALOGUE SUMMARIES
              </h3>
              <div className="space-y-2">
                {selectedLead.calls && selectedLead.calls.length > 0 ? (
                  selectedLead.calls.map((call, idx) => (
                    <div key={idx} className="p-3 bg-zinc-900 rounded border border-zinc-800 space-y-1.5 text-xs">
                      <div className="flex justify-between items-center text-zinc-400">
                        <span className="text-white font-bold">{call.call_id}</span>
                        <span>{call.duration_seconds}s | SENTIMENT: {call.sentiment?.toUpperCase()}</span>
                      </div>
                      <p className="text-zinc-300 font-sans leading-relaxed">{call.summary}</p>
                      {call.objections && call.objections.length > 0 && (
                        <div className="text-[11px] text-zinc-400">
                          OBJECTIONS: {call.objections.join(', ')}
                        </div>
                      )}
                    </div>
                  ))
                ) : (
                  <p className="text-xs text-zinc-500">No prior call records on file.</p>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
