# AI Agent Coordination & Decision Engine

An AI-powered Business Decision Support System developed as part of the **Infosys Springboard Virtual Internship 7.0**.

The project demonstrates how multiple AI agents can collaborate internally to solve enterprise business problems while presenting a single unified interface to the user.

---

# Project Overview

Modern enterprises require intelligent systems capable of analyzing business problems, coordinating multiple AI capabilities, utilizing business tools, and generating informed decisions.

This project implements a centralized AI Business Decision Engine that internally performs research, planning, tool execution, memory management, and final decision making without exposing individual agents to the user.

The current implementation focuses on the business niche:

**E-Commerce Product Launch Decision Support**

Example Business Problem:

> Should we launch an eco-friendly water bottle for college students?

The system analyzes the request and produces a structured business decision report.

---

# Objectives

The Business Decision Engine is designed to:

- Understand business problems
- Perform business research
- Generate strategic business plans
- Evaluate market opportunities
- Analyze business risks
- Execute business tools when required
- Coordinate AI agents internally
- Store shared business context
- Produce structured business recommendations

---

# Business Niche

The current system specializes in supporting **E-Commerce Product Launch Decisions**.

It helps organizations evaluate whether a new product should be launched by analyzing:

- Business objectives
- Market opportunities
- Business risks
- Financial considerations
- Strategic planning
- Final recommendation

---

# System Architecture

```
                    User
                      │
                      ▼
          Business Decision Problem
                      │
                      ▼
      ┌────────────────────────────┐
      │ Business Decision Engine   │
      └────────────────────────────┘
                      │
     ┌────────────────┼─────────────────┐
     ▼                ▼                 ▼
Research Agent   Planning Agent   Decision Agent
     │                │                 │
     └────────────────┼─────────────────┘
                      │
              Shared Memory
                      │
             Business Tool Manager
                      │
     ┌────────────────┼─────────────────┐
     ▼                ▼                 ▼
 Market Risk     Profit Tool     ROI Tool
     │
     ▼
Business Decision Report
```

---

# Workflow

The user interacts with only one component:

```
User
   │
   ▼
Business Decision Engine
   │
   ▼
Business Tool Selector
   │
   ▼
Business Tools
   │
   ▼
Research Agent
   │
   ▼
Planning Agent
   │
   ▼
Decision Agent
   │
   ▼
Shared Memory
   │
   ▼
Final Business Decision Report
```

The internal AI agents collaborate automatically without requiring any user intervention.

---

# Core Components

## Business Decision Engine

Acts as the central controller of the system.

Responsibilities:

- Receives business requests
- Coordinates AI agents
- Executes business tools
- Stores shared memory
- Generates final reports

---

## Research Agent

Responsible for:

- Business research
- Market analysis
- Opportunity identification
- Risk discovery

---

## Planning Agent

Responsible for:

- Strategy generation
- Action planning
- Business workflow planning
- Implementation roadmap

---

## Decision Agent

Responsible for:

- Combining all agent outputs
- Evaluating tool results
- Generating final recommendations
- Producing business decision reports

---

## Shared Memory

Maintains information generated during execution.

Currently stores:

- Research output
- Planning output
- Tool output
- Final decision
- Business history

---

## Tool Manager

Automatically determines which business tool should be executed.

The user never selects tools manually.

---

## Business Tools

Current tools include:

- Market Risk Analysis
- Profit Calculator
- ROI Calculator
- Break-even Calculator

---

# Current Features

- AI Business Decision Engine
- Multi-Agent Coordination
- Research Agent
- Planning Agent
- Decision Agent
- Shared Memory
- LangChain Integration
- Google Gemini Integration
- Intelligent Tool Selection
- Tool Manager
- Market Risk Analysis
- Profit Calculator
- ROI Calculator
- Break-even Calculator
- Structured Business Decision Report

---

# Technologies Used

- Python
- LangChain
- Google Gemini 2.5 Flash
- Google Generative AI SDK
- Prompt Engineering
- Shared Memory
- Modular Multi-Agent Architecture
- Git
- GitHub
- VS Code

---

# Project Structure

```
AI-Agent-Coordination-Decision-Engine
│
├── agents
│   ├── business_decision_engine.py
│   ├── research_agent.py
│   ├── planning_agent.py
│   └── decision_agent.py
│
├── prompts
│   ├── business_decision_prompt.py
│   ├── research_prompt.py
│   ├── planning_prompt.py
│   └── decision_prompt.py
│
├── tools
│   ├── tool_selector.py
│   ├── tool_manager.py
│   ├── market_risk_tool.py
│   ├── profit_tool.py
│   ├── roi_tool.py
│   └── break_even_tool.py
│
├── memory
│   └── shared_memory.py
│
├── tests
│   └── test_agent.py
│
├── config.py
├── requirements.txt
├── README.md
└── .env
```

---



# Sample Business Problem

```
Should we launch an eco-friendly water bottle for college students?
```

The Business Decision Engine performs:

- Business Research
- Planning
- Market Risk Analysis
- Tool Execution
- Decision Making

and generates a structured business recommendation.

---


# Future Enhancements

- Persistent Long-Term Memory
- Business Knowledge Repository
- REST API using FastAPI
- Interactive Dashboard
- Database Integration
- Workflow Monitoring
- Multi-user Support
- Cloud Deployment (Azure / AWS / GCP)

---

# Author

**Shobika P**

Intern - Infosys Springboard Virtual Internship 7.0

---

# License

This project is developed for educational purposes as part of the Infosys Springboard Virtual Internship 7.0.