# Machine Learning (Experimental & Future Scope)

This directory is reserved for experimental machine learning scripts, Jupyter notebooks, and custom models planned for future phases of the **KrishiRAG** system (e.g., SIH post-hackathon extensions):

## Planned Future Modules:
- **Computer Vision Disease Triage:** Fine-tuning lightweight CNNs/Vision Transformers on Indian plant pathology datasets.
- **Yield & Microclimate Estimation:** Tabular ML models for seasonal crop yield forecasting using soil and weather data.
- **Vernacular Speech Models:** Localized fine-tuning of Whisper or IndicWav2Vec models for Malayalam and regional Indian dialects.

*(Note: Production embeddings and local LLM inference currently run directly within `backend/app/rag/embedder.py` via FastEmbed and `backend/app/llm/gateway.py` via Ollama).*
