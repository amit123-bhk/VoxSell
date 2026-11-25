# VoxSell Architecture & Technical Documentation

## High-Level Architecture Diagram

```mermaid
flowchart TD
    subgraph Client["Client Tier"]
        Browser["React + Vite Dashboard (Web Audio / WS)"]
        Telephony["SIP / Twilio / LiveKit Gateway"]
    end

    subgraph Edge["Gateway & WebSocket Ingestion"]
        WS["FastAPI Streaming WebSocket Layer"]
        BargeIn["Barge-In / Interruption Controller"]
    end

    subgraph Pipeline["Real-Time Audio Pipeline (<1.5s Response)"]
        STT["Deepgram Live STT (Streaming Websocket)"]
        LangDetect["Language Detector (EN / HI / PA)"]
        LLM["Streaming LLM Orchestrator + Tools"]
        RAG["ChromaDB Vector Store (RAG)"]
        TTS["Streaming TTS (Deepgram Aura / Cartesia)"]
    end

    subgraph State["State & Persistence"]
        Redis["Redis (Session State, In-Call Turns, Pub/Sub)"]
        Postgres[("PostgreSQL (Leads, Calls, Transcripts, Bookings)")]
    end

    subgraph Integrations["External Services & Background Tasks"]
        GCal["Google Calendar API"]
        CRM["HubSpot / Native Postgres CRM"]
        SummaryQueue["Async Post-Call Summarization"]
    end

    Browser -->|Audio Stream| WS
    Telephony -->|Audio Stream| WS
    WS --> STT
    WS --> BargeIn
    STT --> LangDetect
    LangDetect --> LLM
    LLM -->|Semantic Retrieval| RAG
    LLM -->|Chunked Sentences| TTS
    TTS -->|PCM Audio Chunks| WS
    BargeIn -.->|Cancel Frame| TTS

    WS <--> Redis
    LLM --> GCal
    LLM --> CRM
    WS --> Postgres
    WS --> SummaryQueue
    SummaryQueue --> Postgres
```

## Architectural Rationale for Scaling (100,000+ Concurrent Scale)
1. **Stateless API/WebSocket Pods**: All active call state and transient audio buffers reside in Redis clusters, allowing horizontal autoscaling behind AWS ALB / Envoy without sticky session fragility.
2. **Streaming Chunk Pipeline**: Audio is not held until speech ends. Streaming transcription triggers speculative LLM sentence completion, feeding TTS before the entire thought finishes, dropping latency under 1.5 seconds.
3. **Decoupled Post-Call Workflows**: BANT scoring finalization, embedding generation, and CRM webhooks execute out-of-band in worker queues (Celery / Redis Streams), keeping the real-time audio thread completely unblocked.
