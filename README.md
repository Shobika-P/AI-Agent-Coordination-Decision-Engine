# Enterprise AI Business Decision Support Workspace

An enterprise-grade **AI Business Decision Support System** developed as part of the **Infosys Springboard Virtual Internship 7.0**.

The workspace orchestrates specialized AI agents using **LangGraph StateGraph**, quantitative financial & market tools, centralized **Gemini API rate-limit/quota shielding**, persistent **SQLite database storage**, **What-If sensitivity modeling**, and a **Dark-Blue Enterprise React Dashboard**.

---

## 🌟 Key Features

1. **Centralized Gemini Client & Quota Shield**:
   - Single point of execution for all AI prompts across all agents.
   - Built-in exponential backoff, rate-limit (429/ResourceExhausted) detection, normalized MD5 query caching, request counting, and token telemetry tracking.
   - **Automatic DEMO/CACHE Fallback Mode**: If Gemini API quota is exhausted or key is missing, the application automatically uses intelligent cached/demo mode without crashing or blanking out the UI.

2. **Backend LangGraph Orchestration**:
   - `START` ➔ `Tool Selection & Execution` ➔ `Research Agent` ➔ `Planning Agent` ➔ `Decision Agent` ➔ `Report Generation` ➔ `END`.
   - Passes compact structured JSON state between agents to minimize token consumption.
   - Exposes real-time StateGraph execution statuses (`WAITING`, `RUNNING`, `COMPLETED`, `FAILED`, `SKIPPED`) and execution metrics to the React frontend.

3. **Enterprise Workflow Visualization**:
   - Interactive dark-blue visualizer pipeline tracking node execution status in real-time.
   - Clickable graph nodes revealing execution latency, node purpose, and metadata popovers.

4. **Dynamic Unlimited Follow-up Q&A**:
   - Users can ask any custom follow-up questions ("What if we target college students?", "How can we lower CAC?").
   - Maintains full conversation history tied to session ID and persistent database.
   - Protected against API failures so previous reports remain fully readable with inline status notices.

5. **Decision Intelligence Dashboard**:
   - Quantified **Business Viability Score** (0-100), **AI Confidence Level** (%), and **Market Risk Badge** (Low/Medium/High).
   - "Why This Decision?" key strategic drivers.
   - Key Risks & Opportunities grid + Quantitative Tool Analysis observations.

6. **What-If Sensitivity Analysis Engine**:
   - Interactive scenario modeling for Product Price, Monthly Volume, Marketing Budget, CAC, Fixed Costs, and Variable Unit Costs.
   - Computes updated profit, break-even units, updated risk rating, and viability score.

7. **Persistent SQLite Report Library**:
   - Auto-generates concise report titles from business questions.
   - Stores report JSON data, risk ratings, viability scores, and conversation threads in SQLite (`memory/decision_engine.db`).
   - UI features search, risk filtering (ALL/LOW/MEDIUM/HIGH), opening saved reports, downloading, and deleting entries.

8. **Multi-Format Report Export**:
   - Download Executive Assessment reports in **PDF** (ReportLab generated styled document), **JSON**, or **Markdown**.
   - Direct text clipboard copy and print view support.

9. **System Telemetry & Monitoring**:
   - System modal displaying total Gemini requests, cached responses, cache hit rate %, average response latency, token usage breakdown, and storage metrics.

---

## 🏗️ System Architecture

```text
                                 USER
                                  │
                                  ▼
                   ┌─────────────────────────────┐
                   │  Dark-Blue Enterprise UI    │
                   └─────────────────────────────┘
                                  │
                                  ▼
                   ┌─────────────────────────────┐
                   │  Flask REST API (app.py)    │
                   └─────────────────────────────┘
                                  │
                                  ▼
                ┌───────────────────────────────────┐
                │ LangGraph StateGraph Workflow     │
                │                                   │
                │  START                            │
                │    ↓                              │
                │  Business Tool Execution Node     │
                │    ↓                              │
                │  Research Agent Node              │
                │    ↓                              │
                │  Planning Agent Node              │
                │    ↓                              │
                │  Decision Agent Node              │
                │    ↓                              │
                │  Report Compilation Node          │
                │    ↓                              │
                │  END                              │
                └───────────────────────────────────┘
                                  │
                 ┌────────────────┴────────────────┐
                 ▼                                 ▼
    ┌───────────────────────────┐    ┌───────────────────────────┐
    │ Centralized Gemini Client │    │ SQLite Persistent DB     │
    │ (Caching, Telemetry, Demo)│    │ (memory/decision_engine.db│
    └───────────────────────────┘    └───────────────────────────┘
```

---

## 🛠️ Technology Stack

- **Backend**: Python 3.11+, Flask, Flask-CORS, LangGraph, LangChain Google GenAI, SQLite3, ReportLab.
- **Frontend**: React 19, Vite, Axios, Vanilla CSS (Dark Navy Enterprise Design System).
- **AI Models**: Google Gemini 2.5 Flash / Gemini Pro.

---

## 🚀 How to Run the Application

### 1. Prerequisites
Ensure Python 3.11+ and Node.js 18+ are installed on your system.

### 2. Environment Setup
Create a `.env` file in the root directory:

```env
GOOGLE_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.6-flash
PORT=5000
```

*(Note: If `GOOGLE_API_KEY` is not provided or quota is exceeded, the application automatically operates under Demo/Cache Mode without crashing).*

### 3. Start Backend Server
```bash
# Activate virtual environment if present
.\venv\Scripts\activate   # On Windows
source venv/bin/activate  # On Linux/Mac

# Install dependencies if needed
pip install -r requirements.txt

# Run Flask backend
python app.py
```
The backend server starts at `http://127.0.0.1:5000`.

### 4. Start React Frontend
In a new terminal window:

```bash
cd business-decision-ui

# Install dependencies if needed
npm install

# Start development server
npm run dev
```
The frontend application will be available at `http://localhost:5173`.

---

## 📡 API Endpoint Summary

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Health check & system status |
| `POST` | `/generate-report` | Triggers backend LangGraph workflow execution |
| `POST` | `/follow-up` | Processes dynamic context-aware follow-up question |
| `POST` | `/what-if` | Runs sensitivity scenario calculation |
| `GET` | `/reports` | Fetches persistent SQLite Report Library |
| `GET` | `/reports/<id>` | Retrieves single report & conversation thread |
| `DELETE` | `/reports/<id>` | Deletes report from SQLite DB |
| `POST` | `/export-report` | Exports report as PDF, JSON, or Markdown |
| `GET` | `/history` | Returns decision history from SQLite |
| `GET` | `/monitoring` | Returns AI usage & system telemetry metrics |
| `POST` | `/re-run-decision` | Re-evaluates decision stage with adjusted parameters |

---

## 🧪 Verification & Testing
To execute backend verification tests:
```bash
python C:\Users\shobi\.gemini\antigravity\brain\74b2f86b-c269-4eeb-a31e-75186f6ed499\scratch\test_pipeline.py
```
To verify frontend build:
```bash
cd business-decision-ui && npm run build
```
