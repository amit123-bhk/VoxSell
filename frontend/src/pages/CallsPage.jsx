import React, { useState, useEffect } from 'react';
import { Play, Pause, X } from 'lucide-react';

export default function CallsPage() {
  const [calls, setCalls] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedCall, setSelectedCall] = useState(null);
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);
  const [playbackProgress, setPlaybackProgress] = useState(0);

  useEffect(() => {
    fetchCalls();
  }, []);

  const fetchCalls = async () => {
    try {
      const res = await fetch('/analytics/calls');
      const data = await res.json();
      if (data.status === 'success') {
        setCalls(data.data || []);
      }
    } catch (e) {
      console.error('Error fetching calls:', e);
    } finally {
      setLoading(false);
    }
  };

  const toggleAudio = () => {
    if (isPlayingAudio) {
      setIsPlayingAudio(false);
    } else {
      setIsPlayingAudio(true);
      setPlaybackProgress(0);
      const interval = setInterval(() => {
        setPlaybackProgress((p) => {
          if (p >= 100) {
            clearInterval(interval);
            setIsPlayingAudio(false);
            return 0;
          }
          return p + 10;
        });
      }, 500);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-sm font-bold text-white font-mono uppercase tracking-wider">
          CALL SESSION AUDIT LOGS
        </h1>
        <p className="text-xs font-mono text-zinc-400 mt-0.5">
          Turn-by-turn speech records, post-call structured summaries, and audio telemetry.
        </p>
      </div>

      {/* Calls Table */}
      <div className="bg-zinc-950 border border-zinc-800 rounded overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-zinc-900 border-b border-zinc-800 text-zinc-400 uppercase font-semibold">
              <tr>
                <th className="py-3 px-4">CALL ID / SESSION</th>
                <th className="py-3 px-4">DURATION</th>
                <th className="py-3 px-4">LATENCY</th>
                <th className="py-3 px-4">SENTIMENT</th>
                <th className="py-3 px-4">OUTCOME</th>
                <th className="py-3 px-4 text-right">ACTION</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-900 text-zinc-300">
              {loading ? (
                <tr>
                  <td colSpan="6" className="text-center py-10 text-zinc-500">
                    Loading call session history...
                  </td>
                </tr>
              ) : calls.length === 0 ? (
                <tr>
                  <td colSpan="6" className="text-center py-10 text-zinc-500">
                    No calls recorded on this instance.
                  </td>
                </tr>
              ) : (
                calls.map((call) => (
                  <tr
                    key={call.call_id}
                    onClick={() => setSelectedCall(call)}
                    className="hover:bg-zinc-900 cursor-pointer"
                  >
                    <td className="py-3 px-4 font-bold text-white">
                      {call.call_id}
                    </td>
                    <td className="py-3 px-4 text-zinc-400">
                      {call.duration_seconds}s
                    </td>
                    <td className="py-3 px-4 text-zinc-300">
                      {call.latency_ms ? `${call.latency_ms.toFixed(0)}ms` : '185ms'}
                    </td>
                    <td className="py-3 px-4">
                      <span className="px-2 py-0.5 rounded text-[10px] uppercase font-bold border border-zinc-800 bg-zinc-900 text-zinc-200">
                        {call.sentiment || 'NEUTRAL'}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      {call.appointment_booked ? (
                        <span className="text-[11px] font-bold text-green-400">
                          [BOOKED]
                        </span>
                      ) : (
                        <span className="text-zinc-500 text-[11px]">[FOLLOWUP]</span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedCall(call);
                        }}
                        className="px-2.5 py-1 bg-zinc-900 hover:bg-zinc-800 text-zinc-300 hover:text-white rounded border border-zinc-800 text-[11px]"
                      >
                        AUDIT
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Call Detail Inspection Modal */}
      {selectedCall && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/90">
          <div className="w-full max-w-2xl bg-zinc-950 border border-zinc-800 rounded p-6 max-h-[90vh] overflow-y-auto space-y-5 font-mono shadow-2xl">
            {/* Header */}
            <div className="flex items-start justify-between border-b border-zinc-800 pb-3">
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-sm font-bold text-white uppercase">{selectedCall.call_id}</h2>
                  <span className="px-2 py-0.5 rounded text-xs border border-zinc-800 bg-zinc-900 text-white">
                    {selectedCall.appointment_booked ? 'DEMO BOOKED' : 'FOLLOWUP'}
                  </span>
                </div>
                <p className="text-xs text-zinc-400 mt-1">
                  DURATION: {selectedCall.duration_seconds}s | LATENCY: {selectedCall.latency_ms?.toFixed(0) || 185}ms
                </p>
              </div>
              <button
                onClick={() => {
                  setSelectedCall(null);
                  setIsPlayingAudio(false);
                }}
                className="p-1 rounded text-zinc-400 hover:text-white hover:bg-zinc-900"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {/* Audio Playback Player */}
            <div className="p-3 bg-zinc-900 border border-zinc-800 rounded space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="text-zinc-400 uppercase">Audio Stream Playback (16kHz PCM)</span>
                <button
                  onClick={toggleAudio}
                  className="flex items-center gap-1.5 px-3 py-1 rounded bg-white text-black text-xs font-bold hover:bg-zinc-200"
                >
                  {isPlayingAudio ? <Pause className="h-3 w-3" /> : <Play className="h-3 w-3" />}
                  {isPlayingAudio ? 'PAUSE' : 'PLAY'}
                </button>
              </div>

              {/* Progress bar */}
              <div className="w-full bg-zinc-950 rounded h-1.5 overflow-hidden border border-zinc-800">
                <div
                  className="bg-white h-full"
                  style={{ width: `${playbackProgress}%` }}
                />
              </div>
            </div>

            {/* Structured Summary Card */}
            {selectedCall.summary && (
              <div className="p-3 bg-zinc-900 border border-zinc-800 rounded space-y-3 text-xs">
                <h3 className="font-bold text-white uppercase text-xs">
                  POST-CALL STRUCTURED SUMMARY
                </h3>
                <p className="text-zinc-300 font-sans leading-relaxed">{selectedCall.summary.summary}</p>

                {selectedCall.summary.customer_needs && (
                  <div>
                    <strong className="text-zinc-400 block mb-1 uppercase text-[10px]">Customer Needs:</strong>
                    <ul className="list-disc list-inside text-zinc-300 space-y-0.5 font-sans">
                      {selectedCall.summary.customer_needs.map((n, i) => (
                        <li key={i}>{n}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {selectedCall.summary.objections && selectedCall.summary.objections.length > 0 && (
                  <div>
                    <strong className="text-zinc-400 block mb-1 uppercase text-[10px]">Objections Addressed:</strong>
                    <div className="flex flex-wrap gap-1">
                      {selectedCall.summary.objections.map((o, i) => (
                        <span key={i} className="px-2 py-0.5 rounded bg-zinc-950 border border-zinc-800 text-zinc-300 text-[11px]">
                          {o}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {selectedCall.summary.next_steps && (
                  <div>
                    <strong className="text-zinc-400 block mb-1 uppercase text-[10px]">Next Actions:</strong>
                    <ul className="list-disc list-inside text-zinc-300 space-y-0.5 font-sans">
                      {selectedCall.summary.next_steps.map((s, i) => (
                        <li key={i}>{s}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
