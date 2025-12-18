Local-First Autonomous Inbox Agent

📧 Smart Inbox Agent (Privacy-First)
An autonomous email organization system that runs 100% locally. It connects to your Gmail via OAuth, fetches unread messages, and uses a local LLM (Llama 3.2) to categorize and archive emails based on their semantic content, not just keywords.

🚀 Key Features
Zero-Data Leakage: Uses Ollama to run inference on-device. No email contents are ever sent to OpenAI, Anthropic, or Google Cloud servers.

Semantic Understanding: Can tell the difference between a "receipt" and a "bank alert," or a "recruiter" and a "cold sales pitch," which regex filters cannot do.

Batch Processing: Implements asynchronous batching with tqdm visualization to handle high-volume inboxes (500+ emails) without hitting API rate limits.

Configurable Logic: Sorting categories (Finance, Important, Spam) are decoupled from the code, allowing for easy logic updates.

🛠️ Technical Implementation
Authentication: Google OAuth 2.0 for secure, token-based access (no passwords stored).

Inference: Connected Python to a locally hosted Llama 3.2 instance via LangChain.

Resiliency: Built with error handling to manage API timeouts and model hallucinations gracefully during batch operations.