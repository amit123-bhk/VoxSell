# Frequently Asked Questions (FAQs)

### Q: How fast does VoxSell respond during a live call?
A: VoxSell targets an end-to-end voice turnaround of under 1.5 seconds by utilizing streaming Speech-to-Text (STT), speculative sentence-boundary token streaming from LLM, and streaming Text-to-Speech (TTS).

### Q: Which languages can VoxSell speak fluently?
A: VoxSell natively detects and switches between English, Hindi, and Punjabi in real-time, even when leads mix languages within a single sentence (Hinglish/Punglish).

### Q: Can VoxSell book meetings directly into my calendar?
A: Yes. VoxSell has native Google Calendar tool-calling capabilities. It checks real-time slot availability, books the event, generates a Google Meet link, and emails the invite to the prospect.

### Q: Does it integrate with my existing CRM?
A: Out of the box, VoxSell integrates with HubSpot and provides an embedded PostgreSQL CRM with full REST APIs and webhooks for custom pipelines.

### Q: What happens if a lead interrupts the agent while speaking?
A: VoxSell includes an instant interruption / barge-in handler. As soon as user speech is detected by the streaming STT, active TTS playback and LLM generation buffers are immediately halted.
