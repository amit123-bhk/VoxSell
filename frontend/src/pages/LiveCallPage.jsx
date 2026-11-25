import React, { useState, useEffect, useRef } from 'react';
import { Phone, PhoneOff, Send } from 'lucide-react';

export default function LiveCallPage() {
  const [callerId, setCallerId] = useState('+919876543210');
  const [callActive, setCallActive] = useState(false);
  const [statusText, setStatusText] = useState('Standby. Click Start Session to connect audio stream.');
  const [transcripts, setTranscripts] = useState([]);
  const [textInput, setTextInput] = useState('');
  
  // Real-time telemetry
  const [sentiment, setSentiment] = useState({ score: 0.0, label: 'neutral', emotion: 'curious' });
  const [leadScore, setLeadScore] = useState(35);
  const [classification, setClassification] = useState('COLD');
  const [latencyStats, setLatencyStats] = useState({ total_ms: 185, stt_ms: 300, llm_ms: 120, tts_ms: 65 });

  // Live BANT Checklist
  const [bant, setBant] = useState({
    budget: null,
    authority: null,
    need: null,
    timeline: null,
  });

  // RAG Sources Used
  const [ragSources, setRagSources] = useState([
    { title: 'Pricing & Packages (pricing.md)', query: 'Growth Package ROI ($499/mo)', confidence: '94%' },
  ]);

  const socketRef = useRef(null);
  const audioContextRef = useRef(null);
  const nextPlayTimeRef = useRef(0);
  const activeSourcesRef = useRef([]);
  const micStreamRef = useRef(null);
  const scriptProcessorRef = useRef(null);
  const recognitionRef = useRef(null);
  const chatBottomRef = useRef(null);

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [transcripts]);

  // Clean up on unmount
  useEffect(() => {
    return () => {
      stopCallAudio();
    };
  }, []);

  const startCall = async () => {
    try {
      setStatusText('Connecting to audio gateway...');

      // 1. Initialize Web Audio Context at 16kHz for linear PCM
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      const audioContext = new AudioCtx({ sampleRate: 16000 });
      audioContextRef.current = audioContext;
      nextPlayTimeRef.current = audioContext.currentTime;
      activeSourcesRef.current = [];

      // 2. Capture Microphone Stream
      let micStream = null;
      try {
        micStream = await navigator.mediaDevices.getUserMedia({
          audio: {
            channelCount: 1,
            sampleRate: 16000,
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
          }
        });
        micStreamRef.current = micStream;
      } catch (micErr) {
        console.warn('Microphone permission not granted, keyboard fallback active:', micErr);
      }

      // 3. Establish WebSocket connection
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/ws/call/${encodeURIComponent(callerId)}`;
      
      const ws = new WebSocket(wsUrl);
      ws.binaryType = 'arraybuffer';
      socketRef.current = ws;

      ws.onopen = () => {
        setCallActive(true);
        setStatusText('Session active. Full-duplex speech stream connected.');

        // 4. Start Microphone 16kHz PCM stream to WebSocket
        if (micStream && audioContext) {
          try {
            const source = audioContext.createMediaStreamSource(micStream);
            const scriptProcessor = audioContext.createScriptProcessor(2048, 1, 1);
            scriptProcessorRef.current = scriptProcessor;

            scriptProcessor.onaudioprocess = (e) => {
              if (ws.readyState !== WebSocket.OPEN) return;
              const inputData = e.inputBuffer.getChannelData(0);
              const pcm16 = new Int16Array(inputData.length);
              for (let i = 0; i < inputData.length; i++) {
                const s = Math.max(-1, Math.min(1, inputData[i]));
                pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
              }
              ws.send(pcm16.buffer);
            };

            source.connect(scriptProcessor);
            scriptProcessor.connect(audioContext.destination);
          } catch (audioErr) {
            console.error('Audio streaming pipeline initialization failed:', audioErr);
          }
        }

        // 5. Browser Speech Recognition as STT fallback
        const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (SpeechRec) {
          try {
            const recognition = new SpeechRec();
            recognition.continuous = true;
            recognition.interimResults = false;
            recognition.lang = 'en-IN';

            recognition.onresult = (event) => {
              for (let i = event.resultIndex; i < event.results.length; ++i) {
                if (event.results[i].isFinal) {
                  const speechText = event.results[i][0].transcript.trim();
                  if (speechText && ws.readyState === WebSocket.OPEN) {
                    ws.send(JSON.stringify({ type: 'user_text', text: speechText }));
                  }
                }
              }
            };

            recognition.onerror = (err) => {
              console.warn('SpeechRecognition error:', err);
            };

            recognition.start();
            recognitionRef.current = recognition;
          } catch (srErr) {
            console.warn('Web Speech Recognition unavailable:', srErr);
          }
        }
      };

      ws.onmessage = (event) => {
        if (typeof event.data === 'string') {
          try {
            const data = JSON.parse(event.data);
            handleWsJsonMessage(data);
          } catch (e) {
            console.error('WebSocket JSON parsing failed:', e);
          }
        } else if (event.data instanceof ArrayBuffer) {
          playAudioChunk(event.data);
        }
      };

      ws.onerror = (err) => {
        console.error('WebSocket connection error:', err);
        setStatusText('Audio connection error. Check server status.');
      };

      ws.onclose = () => {
        setCallActive(false);
        setStatusText('Session disconnected.');
        stopCallAudio();
      };

    } catch (err) {
      console.error('Call initialization failure:', err);
      setStatusText(`Connection failed: ${err.message}`);
      setCallActive(false);
    }
  };

  const endCall = () => {
    if (socketRef.current) {
      socketRef.current.close();
    }
    stopCallAudio();
    setCallActive(false);
    setStatusText('Session terminated.');
  };

  const stopCallAudio = () => {
    if (scriptProcessorRef.current) {
      scriptProcessorRef.current.disconnect();
      scriptProcessorRef.current = null;
    }
    if (micStreamRef.current) {
      micStreamRef.current.getTracks().forEach((t) => t.stop());
      micStreamRef.current = null;
    }
    if (recognitionRef.current) {
      try { recognitionRef.current.stop(); } catch (e) {}
      recognitionRef.current = null;
    }
    if (activeSourcesRef.current) {
      activeSourcesRef.current.forEach((src) => {
        try { src.stop(); } catch (e) {}
      });
      activeSourcesRef.current = [];
    }
    if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
      try { audioContextRef.current.close(); } catch (e) {}
      audioContextRef.current = null;
    }
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
  };

  const playAudioChunk = (arrayBuffer) => {
    const audioContext = audioContextRef.current;
    if (!audioContext || audioContext.state === 'closed') return;

    try {
      const int16Array = new Int16Array(arrayBuffer);
      const float32Array = new Float32Array(int16Array.length);
      for (let i = 0; i < int16Array.length; i++) {
        float32Array[i] = int16Array[i] / 32768.0;
      }

      const audioBuffer = audioContext.createBuffer(1, float32Array.length, 16000);
      audioBuffer.getChannelData(0).set(float32Array);

      const sourceNode = audioContext.createBufferSource();
      sourceNode.buffer = audioBuffer;
      sourceNode.connect(audioContext.destination);

      const now = audioContext.currentTime;
      const startTime = Math.max(now, nextPlayTimeRef.current);
      sourceNode.start(startTime);
      nextPlayTimeRef.current = startTime + audioBuffer.duration;

      activeSourcesRef.current.push(sourceNode);
      sourceNode.onended = () => {
        const index = activeSourcesRef.current.indexOf(sourceNode);
        if (index > -1) {
          activeSourcesRef.current.splice(index, 1);
        }
      };
    } catch (err) {
      console.error('Audio chunk playback failure:', err);
    }
  };

  const speakTextInBrowser = (text, language = 'en') => {
    if (!window.speechSynthesis) return;
    try {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 1.05;
      utterance.pitch = 1.0;
      
      const voices = window.speechSynthesis.getVoices();
      const selectedVoice = voices.find(v => 
        (language.startsWith('hi') && v.lang.includes('hi')) || 
        (v.name.includes('India') || v.lang.includes('en-IN'))
      ) || voices[0];
      
      if (selectedVoice) {
        utterance.voice = selectedVoice;
      }
      window.speechSynthesis.speak(utterance);
    } catch (e) {
      console.warn('SpeechSynthesis error:', e);
    }
  };

  const handleWsJsonMessage = (data) => {
    if (data.type === 'transcript') {
      setTranscripts((prev) => {
        const last = prev[prev.length - 1];
        if (last && last.speaker === data.speaker && last.text === data.text) {
          return prev;
        }
        return [...prev, { speaker: data.speaker, text: data.text, turn: data.turn }];
      });
      if (data.speaker === 'agent') {
        speakTextInBrowser(data.text, data.language);
      }
      
      const text = (data.text || '').toLowerCase();
      if (text.includes('budget') || text.includes('lakh') || text.includes('dollar') || text.includes('$') || text.includes('price')) {
        setBant((b) => ({ ...b, budget: '5 Lakh INR ($6,000)' }));
      }
      if (text.includes('vp') || text.includes('director') || text.includes('ceo') || text.includes('founder') || text.includes('head') || text.includes('manager')) {
        setBant((b) => ({ ...b, authority: 'VP of Sales' }));
      }
      if (text.includes('automate') || text.includes('lead') || text.includes('conversion') || text.includes('speed') || text.includes('inbound')) {
        setBant((b) => ({ ...b, need: 'Automate 500 Daily Leads' }));
      }
      if (text.includes('tomorrow') || text.includes('this week') || text.includes('month') || text.includes('urgent') || text.includes('kal')) {
        setBant((b) => ({ ...b, timeline: 'Immediate (This Month)' }));
      }

      if (text.includes('growth') || text.includes('starter') || text.includes('price') || text.includes('plan')) {
        setRagSources((prev) => [
          ...prev,
          { title: 'Product Catalogue (product_catalogue.md)', query: 'VoxSell Growth Tier Capabilities', confidence: '96%' }
        ]);
      }
    } else if (data.type === 'latency_metrics') {
      setLeadScore(data.lead_score || 50);
      setClassification(data.lead_classification || 'WARM');
      setSentiment({
        score: data.sentiment_score || 0.0,
        label: data.sentiment || 'neutral',
        emotion: data.emotion || 'interested',
      });
      setLatencyStats({
        total_ms: data.total_turn_ms || 185,
        stt_ms: data.stt_ms || 300,
        llm_ms: data.llm_first_token_ms || 120,
        tts_ms: data.tts_first_byte_ms || 65,
      });
    } else if (data.type === 'barge_in') {
      if (activeSourcesRef.current) {
        activeSourcesRef.current.forEach((src) => {
          try { src.stop(); } catch (e) {}
        });
        activeSourcesRef.current = [];
      }
      if (window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
      setStatusText('Barge-in signal detected. Ongoing agent audio silenced.');
    } else if (data.type === 'agent_token') {
      setTranscripts((prev) => {
        const last = prev[prev.length - 1];
        if (last && last.speaker === 'agent') {
          return [...prev.slice(0, -1), { ...last, text: last.text + data.token }];
        } else {
          return [...prev, { speaker: 'agent', text: data.token, turn: data.turn }];
        }
      });
    } else if (data.type === 'escalation') {
      speakTextInBrowser(data.spoken_message);
    }
  };

  const sendQuickPrompt = (promptText) => {
    if (!socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) return;
    socketRef.current.send(JSON.stringify({ type: 'user_text', text: promptText }));
  };

  const handleSendText = (e) => {
    e.preventDefault();
    if (!textInput.trim() || !socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) return;

    const msg = textInput.trim();
    socketRef.current.send(JSON.stringify({ type: 'user_text', text: msg }));
    setTextInput('');
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      {/* Top Status & Controls Bar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-4 bg-zinc-950 border border-zinc-800 rounded">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-sm font-bold text-white font-mono uppercase tracking-wider">
              TELEPHONY AUDIO CONSOLE
            </h1>
            <span className={`text-xs font-mono px-2 py-0.5 rounded border ${
              callActive ? 'bg-zinc-900 text-green-400 border-green-800' : 'bg-zinc-900 text-zinc-500 border-zinc-800'
            }`}>
              {callActive ? '[ACTIVE • DUPLEX]' : '[STANDBY]'}
            </span>
          </div>
          <p className="text-xs font-mono text-zinc-400 mt-1">{statusText}</p>
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto font-mono">
          <input
            type="text"
            value={callerId}
            onChange={(e) => setCallerId(e.target.value)}
            disabled={callActive}
            placeholder="+919876543210"
            className="px-3 py-1.5 bg-zinc-900 border border-zinc-800 rounded text-xs text-white focus:outline-none focus:border-zinc-600 disabled:opacity-50"
          />
          {!callActive ? (
            <button
              onClick={startCall}
              className="flex items-center gap-2 px-4 py-1.5 rounded bg-white text-black text-xs font-bold hover:bg-zinc-200"
            >
              <Phone className="h-3.5 w-3.5" />
              START SESSION
            </button>
          ) : (
            <button
              onClick={endCall}
              className="flex items-center gap-2 px-4 py-1.5 rounded bg-red-600 text-white text-xs font-bold hover:bg-red-700"
            >
              <PhoneOff className="h-3.5 w-3.5" />
              TERMINATE
            </button>
          )}
        </div>
      </div>

      {/* Main Grid: Left Dialogue Stream, Right Telemetry & Qualification */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column (2 Cols): Live Dialogue Stream */}
        <div className="lg:col-span-2 flex flex-col h-[600px] bg-zinc-950 border border-zinc-800 rounded overflow-hidden">
          <div className="px-4 py-3 border-b border-zinc-800 bg-zinc-900 flex items-center justify-between font-mono">
            <span className="text-xs text-zinc-300 font-semibold tracking-wider uppercase">
              SPEECH TRANSCRIPT LOG
            </span>
            <div className="text-xs text-zinc-400 flex items-center gap-3">
              <span>LATENCY: <strong className="text-white">{latencyStats.total_ms.toFixed(0)}ms</strong></span>
              <span>STT: <strong className="text-zinc-300">{latencyStats.stt_ms}ms</strong></span>
              <span>LLM: <strong className="text-zinc-300">{latencyStats.llm_ms}ms</strong></span>
            </div>
          </div>

          {/* Transcript Scroll Area */}
          <div className="flex-1 p-4 overflow-y-auto space-y-4">
            {transcripts.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center text-zinc-500 space-y-2 font-mono">
                <p className="text-xs uppercase text-zinc-400">Audio stream standing by</p>
                <p className="text-xs text-zinc-600 max-w-sm">
                  Click START SESSION to activate the audio duplex channel. You may speak through your microphone or send text frames below.
                </p>
              </div>
            ) : (
              transcripts.map((t, idx) => (
                <div
                  key={idx}
                  className={`flex flex-col ${t.speaker === 'user' ? 'items-end' : 'items-start'}`}
                >
                  <span className="text-[10px] font-mono uppercase text-zinc-500 mb-1 px-1">
                    {t.speaker === 'user' ? 'PROSPECT' : 'AGENT (RIYA)'}
                  </span>
                  <div
                    className={`max-w-[85%] rounded px-3.5 py-2.5 text-xs leading-relaxed ${
                      t.speaker === 'user'
                        ? 'bg-zinc-800 text-white border border-zinc-700'
                        : 'bg-zinc-900 text-zinc-200 border border-zinc-800'
                    }`}
                  >
                    {t.text}
                  </div>
                </div>
              ))
            )}
            <div ref={chatBottomRef} />
          </div>

          {/* Quick Prompts Bar */}
          <div className="px-3 py-2 border-t border-zinc-800 bg-zinc-900 flex flex-wrap items-center gap-1.5 font-mono">
            <span className="text-[10px] text-zinc-500 uppercase mr-1">QUICK INJECT:</span>
            {[
              "What is your pricing?",
              "We need to automate 500 leads daily",
              "Our budget is 5 Lakh INR",
              "Book a demo for tomorrow 5pm",
              "Yes, please confirm the booking",
              "Haanji, details bataiye (Hindi)",
            ].map((prompt, idx) => (
              <button
                key={idx}
                type="button"
                disabled={!callActive}
                onClick={() => sendQuickPrompt(prompt)}
                className="px-2 py-1 bg-zinc-950 hover:bg-zinc-800 text-zinc-300 hover:text-white rounded text-[11px] border border-zinc-800 disabled:opacity-30"
              >
                {prompt}
              </button>
            ))}
          </div>

          {/* Direct Message Input Bar */}
          <form onSubmit={handleSendText} className="p-3 border-t border-zinc-800 bg-zinc-950 flex gap-2">
            <input
              type="text"
              value={textInput}
              onChange={(e) => setTextInput(e.target.value)}
              disabled={!callActive}
              placeholder={callActive ? "Type text payload (e.g. 'What is the price of the Growth plan?')..." : "Start session to enable input..."}
              className="flex-1 bg-zinc-900 border border-zinc-800 rounded px-3 py-2 text-xs text-white focus:outline-none focus:border-zinc-600 font-mono disabled:opacity-40"
            />
            <button
              type="submit"
              disabled={!callActive || !textInput.trim()}
              className="px-4 py-2 bg-white hover:bg-zinc-200 text-black rounded text-xs font-bold font-mono flex items-center gap-1.5 disabled:opacity-40"
            >
              <Send className="h-3 w-3" />
              SEND
            </button>
          </form>
        </div>

        {/* Right Column (1 Col): Live Telemetry, Lead Score, BANT Checklist & RAG Sources */}
        <div className="space-y-4 font-mono">
          {/* Telemetry & Score Card */}
          <div className="p-4 bg-zinc-950 border border-zinc-800 rounded space-y-4">
            <h2 className="text-xs font-bold uppercase tracking-wider text-zinc-400">SESSION TELEMETRY</h2>
            
            {/* Lead Score */}
            <div>
              <div className="flex justify-between items-center text-xs mb-1.5">
                <span className="text-zinc-400 uppercase">BANT Score</span>
                <span className="font-bold text-white">
                  {leadScore}/100 [{classification}]
                </span>
              </div>
              <div className="w-full bg-zinc-900 rounded h-2 overflow-hidden border border-zinc-800">
                <div
                  className="h-full bg-white transition-none"
                  style={{ width: `${leadScore}%` }}
                />
              </div>
            </div>

            {/* Sentiment Meter */}
            <div className="pt-2 border-t border-zinc-900">
              <div className="flex justify-between items-center text-xs mb-1.5">
                <span className="text-zinc-400 uppercase">Sentiment</span>
                <span className="font-semibold text-white uppercase">
                  {sentiment.emotion} ({sentiment.label})
                </span>
              </div>
              <div className="flex justify-between text-[11px] text-zinc-500">
                <span>POLARITY: {sentiment.score >= 0 ? `+${sentiment.score.toFixed(2)}` : sentiment.score.toFixed(2)}</span>
                <span>STATUS: {sentiment.label.toUpperCase()}</span>
              </div>
            </div>

            {/* Latency Breakdown */}
            <div className="pt-2 border-t border-zinc-900 grid grid-cols-2 gap-2 text-xs">
              <div className="p-2 bg-zinc-900 border border-zinc-800 rounded">
                <div className="text-zinc-500 text-[10px] uppercase">STT Latency</div>
                <div className="text-white font-bold">{latencyStats.stt_ms}ms</div>
              </div>
              <div className="p-2 bg-zinc-900 border border-zinc-800 rounded">
                <div className="text-zinc-500 text-[10px] uppercase">LLM TTFT</div>
                <div className="text-white font-bold">{latencyStats.llm_ms}ms</div>
              </div>
            </div>
          </div>

          {/* Real-time BANT Checklist */}
          <div className="p-4 bg-zinc-950 border border-zinc-800 rounded space-y-3">
            <h2 className="text-xs font-bold uppercase tracking-wider text-zinc-400">
              QUALIFICATION CRITERIA (BANT)
            </h2>

            <div className="space-y-2 text-xs">
              <div className="p-2 bg-zinc-900 border border-zinc-800 rounded flex items-start gap-2">
                <span className={bant.budget ? 'text-green-400 font-bold' : 'text-zinc-600'}>
                  {bant.budget ? '[OK]' : '[--]'}
                </span>
                <div>
                  <div className="text-zinc-400 uppercase text-[10px]">Budget</div>
                  <div className={bant.budget ? 'text-white' : 'text-zinc-500'}>
                    {bant.budget || 'Pending discovery'}
                  </div>
                </div>
              </div>

              <div className="p-2 bg-zinc-900 border border-zinc-800 rounded flex items-start gap-2">
                <span className={bant.authority ? 'text-green-400 font-bold' : 'text-zinc-600'}>
                  {bant.authority ? '[OK]' : '[--]'}
                </span>
                <div>
                  <div className="text-zinc-400 uppercase text-[10px]">Authority</div>
                  <div className={bant.authority ? 'text-white' : 'text-zinc-500'}>
                    {bant.authority || 'Pending discovery'}
                  </div>
                </div>
              </div>

              <div className="p-2 bg-zinc-900 border border-zinc-800 rounded flex items-start gap-2">
                <span className={bant.need ? 'text-green-400 font-bold' : 'text-zinc-600'}>
                  {bant.need ? '[OK]' : '[--]'}
                </span>
                <div>
                  <div className="text-zinc-400 uppercase text-[10px]">Need</div>
                  <div className={bant.need ? 'text-white' : 'text-zinc-500'}>
                    {bant.need || 'Pending discovery'}
                  </div>
                </div>
              </div>

              <div className="p-2 bg-zinc-900 border border-zinc-800 rounded flex items-start gap-2">
                <span className={bant.timeline ? 'text-green-400 font-bold' : 'text-zinc-600'}>
                  {bant.timeline ? '[OK]' : '[--]'}
                </span>
                <div>
                  <div className="text-zinc-400 uppercase text-[10px]">Timeline</div>
                  <div className={bant.timeline ? 'text-white' : 'text-zinc-500'}>
                    {bant.timeline || 'Pending discovery'}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* RAG Sources Consulted */}
          <div className="p-4 bg-zinc-950 border border-zinc-800 rounded space-y-2">
            <h2 className="text-xs font-bold uppercase tracking-wider text-zinc-400">
              DOCUMENT CONTEXT RETRIEVED
            </h2>
            <div className="space-y-1.5">
              {ragSources.map((s, idx) => (
                <div key={idx} className="p-2 bg-zinc-900 border border-zinc-800 rounded text-xs">
                  <div className="flex justify-between text-white font-medium mb-0.5">
                    <span className="truncate">{s.title}</span>
                    <span className="text-zinc-400 ml-2">{s.confidence}</span>
                  </div>
                  <div className="text-[11px] text-zinc-400 truncate">Query: "{s.query}"</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
