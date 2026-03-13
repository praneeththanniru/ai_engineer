# AI Engineer – Autonomous Task Agent

📌 **Overview**  
Experimental autonomous AI agent designed to automate software development, DevOps workflows, and task execution using Large Language Models (LLMs).  
This project explores **multi-agent orchestration, task reasoning, and containerized environments** for AI-driven automation.

---

🏗 **System Design**

**Core Components:**

- `main.py` – Agent entry point  
- `app/` – Modular core logic  
- `workspace/` – Execution workspace for generated code  
- `Dockerfile` – Container configuration  
- `docker-compose.yml` – Multi-service orchestration  
- `.env` – Environment-based configuration  

**LLM Pipeline:**

| Role | Model | Purpose |
|------|-------|---------|
| Architect | Llama 3.1 8B | Breaks tasks into step-by-step plans |
| Lead Developer | Qwen 2.5-Coder 14B | Generates core code |
| Debugger | DeepSeek-Coder 6.7B | Optimizes and fixes code |
| Quick Edits | Qwen 2.5-Coder 7B | Fast modifications and small tasks |
| Documentation | Llama 3.2 | Explains code and generates docs |

---

🛠 **Tech Stack**

- Python  
- Docker & Docker Compose  
- LLM Integration (via Ollama)  
- Environment-based configuration (`.env`)  
- ChromaDB (RAG / knowledge management)

---

⚙️ **Architecture Principles**

- Modular task orchestration  
- Containerized runtime for reproducibility  
- Sequential multi-LLM execution (safe memory usage)  
- Configurable environment variables  
- Experimental autonomous reasoning workflow

---

🚧 **Current Status**

- Prototype Version: v0.1.x  
- Sequential multi-agent LLM execution working  
- Modular workspace & task memory implemented  
- RAG knowledge integration functional  

---

🔮 **Future Roadmap**

- Improved reasoning pipelines  
- Multi-agent collaboration & handoff architecture  
- Persistent task memory and task prioritization  
- External API integrations (Email, WhatsApp, Web automation)  
- Advanced logging, monitoring, and dashboard  
- Full app automation from idea → deployment  

---

👨‍💻 **Author**

**Praneeth Thanniru**  
AI-Focused Software Developer | Python, Firebase, LLMs, ML/DL  

📬 **Connect**

- LinkedIn: [thanniru-praneeth](https://www.linkedin.com/in/thanniru-praneeth/)  
- Portfolio: [indivetlabs.com](https://indivetlabs.com)  
- Email: thannirupraneeth3@gmail.com
