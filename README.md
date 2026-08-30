#  Enterprise Workflow Platform with Decision Automation System

An enterprise-grade **AI Workflow Platform & Decision Automation System** where specialized AI agents collaborate to analyze arbitrary business problems, perform research and planning, execute quantitative calculations, make strategic decisions, maintain conversational context, and generate structured decision intelligence reports.

---

## 🌟 Key Capabilities & Features

1. **Multi-Agent LangGraph Orchestration**:
   - Specialized agents orchestrated via a compiled LangGraph `StateGraph`:
     - **Tool Node**: Selects and executes quantitative business models (`break_even_tool`, `profit_tool`, `roi_tool`, `market_risk_tool`).
     - **Research Agent**: Performs deep, domain-specific market analysis, competitive assessment, customer segmentation, and strategic risk/opportunity identification.
     - **Planning Agent**: Derives a structured, multi-phase execution roadmap from market context.
     - **Decision Agent**: Synthesizes qualitative insights, execution roadmap, and quantitative financial metrics into a final recommendation with an executive Viability Score (0–100) and AI Confidence Level.
     - **Report Node**: Validates schema compliance, records performance telemetry, logs to persistent SQLite storage, and maintains session state.

2. **Reliable LLM Integration with Gemini**:
   - Centralized `GeminiClient` wrapper with configurable request timeout (default `45s`), preventing premature timeouts on complex structured prompts.
   - Comprehensive error classification distinguishing between invalid API keys (`AUTH`), quota rate limits (`QUOTA`), model deprecations (`MODEL_NOT_FOUND`), transient network issues (`TRANSIENT`), and timeouts (`TIMEOUT`).
   - Priority fallback chain: Primary model (`gemini-3.6-flash`) with fast secondary models (`gemini-3.1-flash-lite`, `gemini-3.7-flash`).
   - Rational circuit breaker with configurable cooldowns that never falsely locks out healthy API connections.

3. **Transparent Analysis Source Tagging & Safe Caching**:
   - Reports clearly display their provenance:
     - 🟢 **LIVE_AI**: Fresh live LLM execution through the multi-agent workflow.
     - 🔵 **LIVE_CACHE**: In-memory exact query cache hit.
     - 🟠 **FALLBACK**: Transparent offline protection mode when live LLM is unavailable.
   - `force_refresh: true` support in API requests to bypass cache on demand.
   - Fallback responses are never cached as high-quality AI outputs.

4. **Deterministic Sensitivity Analysis (What-If Engine)**:
   - Interactive financial simulation of Product Price, Monthly Volume, Marketing Spend, Customer Acquisition Cost (CAC), Fixed Costs, and Variable Costs.
   - Computes unit contribution margins, break-even thresholds, net profits, and updated viability scoring.

5. **Dynamic Follow-Up Reasoning**:
   - Conversational Q&A utilizing the original business task, report findings, and previous conversation history.
   - Incorporates deterministic financial recalculations for pricing and marketing scenario questions.

6. **Persistent SQLite Report Library & Multi-Format Export**:
   - Automatic concise title generation from business queries.
   - Persistent storage of report JSON, risk levels, viability scores, and conversation threads in SQLite (`memory/decision_engine.db`).
   - Export reports as styled **PDF documents** (via ReportLab), structured **JSON**, or clean **Markdown**.

7. **Real-time Telemetry & Monitoring Dashboard**:
   - Accurately tracks live LLM requests, cache hits, fallback counts, average latency, and token consumption.

---

## 🏗️ System Architecture & Workflow Flow

```text
                                  USER QUERY
                                       │
                                       ▼
                       ┌──────────────────────────────┐
                       │   React + Vite Frontend UI   │
                       └──────────────────────────────┘
                                       │
                                       ▼
                       ┌──────────────────────────────┐
                       │   Flask API (/generate-report│
                       └──────────────────────────────┘
                                       │
                ┌──────────────────────┴──────────────────────┐
                │                                             │
      [Exact Cache Hit]                              [Live AI Workflow]
                │                                             │
                ▼                                             ▼
     ┌─────────────────────┐                   ┌─────────────────────────────┐
     │ Return LIVE_CACHE   │                   │    LangGraph StateGraph     │
     └─────────────────────┘                   └─────────────────────────────┘
                                                              │
                                            ┌─────────────────┴─────────────────┐
                                            ▼                                   ▼
                             ┌─────────────────────────────┐     ┌─────────────────────────────┐
                             │     Business Tool Node      │     │     Research Agent Node     │
                             │ (Profit, Break-Even, Risk)  │     │ (Live Gemini API Analysis)  │
                             └─────────────────────────────┘     └─────────────────────────────┘
                                            │                                   │
                                            └─────────────────┬─────────────────┘
                                                              ▼
                                               ┌─────────────────────────────┐
                                               │     Planning Agent Node     │
                                               │ (Phased Execution Roadmap)  │
                                               └─────────────────────────────┘
                                                              │
                                                              ▼
                                               ┌─────────────────────────────┐
                                               │     Decision Agent Node     │
                                               │ (Multi-Agent Synthesis)     │
                                               └─────────────────────────────┘
                                                              │
                                                              ▼
                                               ┌─────────────────────────────┐
                                               │      Report Node & DB       │
                                               │ (Persistence & Telemetry)   │
                                               └─────────────────────────────┘
                                                              │
                                                              ▼
                                               ┌─────────────────────────────┐
                                               │ Final Structured Report     │
                                               │ (LIVE_AI / FALLBACK)        │
                                               └─────────────────────────────┘
```

---

## 📁 Repository Structure

```text
├── agents/
│   ├── business_decision_engine.py   # Wrapper entrypoint
│   ├── coordination_agent.py          # Agent coordination
│   ├── decision_agent.py              # Executive decision synthesis
│   ├── followup_agent.py              # Follow-up reasoning & calculation
│   ├── planning_agent.py              # Strategic execution roadmap
│   ├── research_agent.py              # Live Gemini strategic market analysis
│   └── suggest_followups_agent.py     # Relevant question recommender
├── business-decision-ui/              # React + Vite Frontend
│   ├── src/
│   │   ├── components/                # UI Components (ReportViewer, Form, WhatIf, etc.)
│   │   ├── services/api.js            # Axios client configuration
│   │   ├── App.jsx                    # Root application component
│   │   └── main.jsx                   # Entry point
│   ├── package.json                   # Frontend dependencies
│   └── vite.config.js                 # Vite configuration
├── graph/
│   └── decision_graph.py              # LangGraph StateGraph orchestration
├── memory/
│   ├── decision_engine.db             # SQLite persistent report database (gitignored)
│   ├── report_db.py                   # SQLite repository & schema manager
│   └── shared_memory.py               # Active session state & telemetry metrics
├── tools/
│   ├── break_even_tool.py             # Deterministic break-even calculator
│   ├── calculator_tool.py             # Arithmetic calculator
│   ├── market_risk_tool.py            # Market risk scoring
│   ├── profit_tool.py                 # Profit margin calculator
│   ├── roi_tool.py                    # Return-on-investment calculator
│   ├── tool_manager.py                # Tool execution router
│   └── tool_selector.py               # Intent-based tool selector
├── utils/
│   ├── gemini_client.py               # Centralized Gemini wrapper & circuit breaker
│   ├── llm_helper.py                  # LLM delegate helper
│   └── pdf_generator.py               # Styled ReportLab PDF exporter
├── tests/                             # Automated test suite
├── app.py                             # Flask REST API entry point
├── config.py                          # Configuration loader
├── Procfile                           # Gunicorn production configuration
├── requirements.txt                   # Backend dependencies
├── .env.example                       # Environment variables template
└── README.md                          # Project documentation
```

---

## ⚙️ Environment Configuration

Create a `.env` file in the root directory:

```env
# Google Gemini API Key (Required for Live AI Analysis)
GOOGLE_API_KEY=your_actual_gemini_api_key_here

# Primary Model Selection
GEMINI_MODEL=gemini-3.6-flash

# Request Timeout (Seconds)
GEMINI_TIMEOUT_SECONDS=45.0

# Circuit Breaker Cooldown (Seconds)
GEMINI_COOLDOWN_SECONDS=15.0

# Server Configuration
PORT=5000
HOST=0.0.0.0
FLASK_DEBUG=false
ALLOWED_ORIGINS=*
```

For the frontend, create `business-decision-ui/.env`:

```env
# Backend API Base URL
VITE_API_BASE_URL=http://127.0.0.1:5000
```

---

## 🚀 Quick Start & Local Execution

### 1. Backend Setup

```bash
# Clone the repository
git clone https://github.com/Shobika-P/AI-Agent-Coordination-Decision-Engine.git
cd AI-Agent-Coordination-Decision-Engine

# Create and activate Python virtual environment
python -m venv venv
# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the Flask Backend Server
python app.py
```

The backend starts at `http://127.0.0.1:5000`.

### 2. Frontend Setup

```bash
# Navigate to the frontend directory
cd business-decision-ui

# Install dependencies
npm install

# Start Vite Development Server
npm run dev
```

Open `http://localhost:5173` in your browser.

---

## 🧪 Testing & Validation

Run the comprehensive test suite to validate all 11 required scenarios:

```bash
python tests/test_all_requirements.py
```

### Verified Test Categories:
1. **New Arbitrary Business Query**: Validates fresh live AI execution and schema validation.
2. **Pricing Strategy Query**: Validates unit margins and price sensitivity modeling.
3. **Market Expansion Query**: Validates competitive positioning and multi-phase roadmap.
4. **Cost Optimization Query**: Validates break-even and profit calculations.
5. **Follow-Up Questions**: Validates context preservation across multiple conversation turns.
6. **What-If Sensitivity Analysis**: Validates deterministic parameter recalculations.
7. **Report History & SQLite Storage**: Validates persistent report logging, retrieval, and search.
8. **Repeated Query Caching**: Validates sub-500ms response time for exact in-memory query hits with `analysis_source == "LIVE_CACHE"`.
9. **Force Refresh**: Validates `force_refresh: true` bypassing cache for fresh live execution.
10. **Empty/Invalid Query Handling**: Validates proper HTTP 400 status code and structured JSON error response.
11. **LLM Failure Scenario**: Validates transparent fallback with `analysis_source == "FALLBACK"` without false AI claims.

---

## 🌐 Production Deployment Guide

### Backend Deployment (e.g. Render / Railway / Heroku / AWS EC2)
- **Startup Command**: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120`
- **Environment Variables**: Set `GOOGLE_API_KEY`, `GEMINI_MODEL`, `ALLOWED_ORIGINS` in your hosting dashboard.
- **Database Note**: Local SQLite persistence works across standard persistent filesystems. For ephemeral serverless containers (e.g., standard Render free tier / AWS Lambda), attach a persistent disk volume to `memory/` or point to a managed PostgreSQL/MySQL database.

### Frontend Deployment (e.g. Vercel / Netlify / Cloudflare Pages)
- **Build Command**: `npm run build`
- **Output Directory**: `dist`
- **Environment Variable**: Set `VITE_API_BASE_URL` to your production backend URL (e.g. `https://your-backend.onrender.com`).

---

## 🔒 Security & GitHub Safety Checklist

- [x] Zero API keys or credentials committed in git.
- [x] `.env` and `.env.*` excluded via `.gitignore`.
- [x] SQLite database files (`*.db`, `*.sqlite`) excluded from version control.
- [x] Node modules (`node_modules/`) and build outputs (`dist/`, `build/`) excluded.
- [x] Python virtual environment (`venv/`) and bytecode (`__pycache__/`) excluded.
- [x] CORS properly configured for production domain whitelisting.

---

## 📄 License

MIT License. See [LICENSE](LICENSE) for details.
