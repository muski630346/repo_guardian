# repo_guardian
# 🛡️ RepoGuardian

> **Autonomous AI Agent System for Code Repository Management**  
> *KLH Hackathon 2025 — Built with Python, CrewAI & Open Source AI*

---

## 📊 At a Glance

| Metric | Value |
|--------|-------|
| 🤖 AI Agents | **8 Specialist Agents** |
| 💡 Innovation Points | **5 Unique Features** |
| 🔧 Manual Steps Needed | **0** |

---

## 🧠 What Is RepoGuardian?

RepoGuardian is an **autonomous multi-agent AI system** that automatically reviews, analyses, and improves code repositories on GitHub and GitLab.

The moment a developer opens a Pull Request, a team of specialised AI agents wakes up, scans the code from multiple angles **simultaneously**, and delivers precise feedback — all without any human intervention.

> **Core Idea:** Instead of one AI model doing everything, RepoGuardian deploys a team of specialist agents — each an expert in its domain — that work in parallel and collaborate to give developers the most complete, accurate code review possible.

---

## 🚨 The Problem We Solve

Modern software teams face a painful bottleneck in the code review process:

- ⏱️ Senior developers spend **2–4 hours every day** manually reviewing Pull Requests
- 🔓 Security vulnerabilities slip through because reviewers can't check every pattern
- 📦 Dependency libraries with known CVEs sit unnoticed for months
- 📉 Code quality degrades slowly — no one tracks complexity or technical debt over time
- 🎲 Feedback is **inconsistent** — it depends on who reviewed, not what the code needs

**RepoGuardian eliminates this bottleneck entirely. It's always on, always consistent, and gets smarter over time.**

---

## ⚙️ How It Works

The entire process is fully automated:

```
1. Developer opens a Pull Request on GitHub or GitLab
       ↓
2. GitHub sends an automatic webhook signal to our FastAPI server — no manual trigger
       ↓
3. Orchestrator Agent reads the changed code and dispatches tasks to all sub-agents
       ↓
4. Four specialist agents run in PARALLEL — Security, Dependency, Code Smell, PR Review
       ↓
5. Each agent reports findings back with severity levels (high / medium / low)
       ↓
6. Inline comments appear directly on the Pull Request — line by line, agent by agent
       ↓
7. Auto-Fix Agent raises a new PR with the fix already applied (for simple issues)
       ↓
8. Repo Health Score updates on the live dashboard — quality improving in real time
```

---

## 🤖 The Agent Team

| Agent | What It Does | Output |
|-------|-------------|--------|
| **Orchestrator Agent** | Receives webhook, reads diff, assigns tasks, aggregates results | Triggers all agents, merges findings |
| **PR Review Agent** | Analyses code logic, naming conventions, structure using LLM | Inline comments on logic and style |
| **Security Agent** | Scans for OWASP vulnerabilities, SQL injection, hardcoded secrets | High/medium/low severity issues |
| **Dependency Agent** | Checks every library against CVE databases, flags unsafe versions | Vulnerable packages with fix versions |
| **Code Smell Agent** | Measures cyclomatic complexity, duplication, dead code per function | Complexity score and debt report |
| **Docs Agent** | Verifies docstrings, README completeness, inline comment coverage | Missing doc locations and suggestions |
| **Auto-Fix Agent** | Writes the fix and raises a new Pull Request automatically | A ready-to-merge fix PR on GitHub |
| **Memory Agent** | Tracks each developer's recurring patterns and personalises feedback | Per-developer recurring issue alerts |

---

## 🌟 5 Innovation Points

### 01 — Multi-Agent Parallel Collaboration
A team of specialists working simultaneously — not one model doing everything.
- Each agent is independently prompted and fine-tuned for its domain
- All agents run in **parallel** — results arrive in seconds, not minutes
- Agents share findings with each other (a security finding can trigger a deeper code review)

### 02 — Autonomous Auto-Fix Pull Requests
The system doesn't just point out problems — **it fixes them and raises a PR**.
- Handles: missing docstrings, unused imports, hardcoded secrets, formatting violations
- Creates a new branch, commits the fix, and opens a ready-to-merge PR
- Developer just reviews and clicks Merge — zero manual effort

### 03 — Repo Health Score (A Credit Score for Code)
One number, **0–100**, that tracks the quality of your entire repository over time.
- Combines findings from all agents into a single weighted score per PR
- Security issues weigh more than style issues — scoring reflects real risk
- Live dashboard shows the score rising as agents help fix problems

### 04 — Developer Memory Agent (Personalised Feedback)
The system **learns each developer's habits** and gives smarter, targeted feedback over time.
- Stores every finding per developer across all PRs
- Repeated mistakes are flagged with higher priority
- Acts like a personal code mentor — tracking growth and recurring weaknesses

### 05 — Open Source LLM Support (Enterprise Ready)
Works with fully open-source models — **no proprietary API required**.
- Supports CodeLlama, Mistral, and LLaMA 3
- Also supports Claude API and OpenAI as premium options
- Fully air-gapped deployment possible — no code ever leaves your servers
- OpenShift compatible for Red Hat enterprise environments

---

## 🆚 RepoGuardian vs GitHub Copilot

| | GitHub Copilot | RepoGuardian |
|--|----------------|-------------|
| **When it runs** | While you're typing code | After code is pushed as a PR |
| **Where it lives** | Inside your code editor | On GitHub / GitLab in the cloud |
| **Architecture** | Single AI model | 8 specialised agents in parallel |
| **Who it helps** | One developer at a time | The entire team simultaneously |
| **Security scanning** | None | Deep OWASP + CVE scanning |
| **Auto-fix** | Suggests snippets only | Raises a full fix Pull Request |
| **Tracks quality** | No | Yes — Repo Health Score + trends |

> **They are complementary, not competing.** Copilot helps you write code. RepoGuardian catches what Copilot missed — before it reaches production.

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| **Language** | Python 3.11+ |
| **Agent Framework** | CrewAI |
| **LLM Backend** | CodeLlama / Mistral (OSS) or Claude API / OpenAI |
| **Security Tools** | Semgrep, Bandit, pip-audit, Safety |
| **GitHub Layer** | FastAPI webhook server + PyGitHub |
| **Dashboard** | Streamlit — live health score, charts, agent activity feed |
| **Storage** | SQLite (quick start) / PostgreSQL (production) |
| **Deployment** | Docker + docker-compose, OpenShift compatible |

---

## 🚀 Quick Start

### Prerequisites

```bash
python 3.11+
docker & docker-compose
git
```

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/repoguardian.git
cd repoguardian

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment variables
cp .env.example .env
# Edit .env with your GitHub token, LLM API keys, etc.

# Run with Docker
docker-compose up --build
```

### Environment Variables

```env
# GitHub
GITHUB_TOKEN=your_github_personal_access_token
WEBHOOK_SECRET=your_webhook_secret

# LLM Backend (choose one)
LLM_PROVIDER=codellama          # codellama | mistral | claude | openai
ANTHROPIC_API_KEY=               # if using Claude
OPENAI_API_KEY=                  # if using OpenAI
OLLAMA_BASE_URL=http://localhost:11434  # if using local Ollama

# Database
DATABASE_URL=sqlite:///./repoguardian.db  # or postgres://...

# Server
PORT=8000
```

### GitHub Webhook Setup

1. Go to your GitHub repository → **Settings → Webhooks → Add webhook**
2. Set Payload URL to: `https://your-server.com/webhook`
3. Content type: `application/json`
4. Secret: same value as `WEBHOOK_SECRET` in your `.env`
5. Select events: **Pull requests**

---

## 📁 Project Structure

```
repoguardian/
├── main.py                    # FastAPI entrypoint & webhook receiver
├── orchestrator/
│   └── orchestrator_agent.py  # Master agent — dispatches sub-agents
├── agents/
│   ├── pr_review_agent.py     # Code logic and style review
│   ├── security_agent.py      # OWASP, secrets, SQL injection scan
│   ├── dependency_agent.py    # CVE and outdated package checks
│   ├── code_smell_agent.py    # Complexity and duplication analysis
│   ├── docs_agent.py          # Docstring and README coverage
│   ├── autofix_agent.py       # Auto-generates fix PRs
│   └── memory_agent.py        # Developer pattern tracking
├── dashboard/
│   └── app.py                 # Streamlit dashboard
├── models/
│   ├── finding.py             # Data models for agent findings
│   └── health_score.py        # Repo Health Score calculator
├── utils/
│   ├── github_client.py       # PyGitHub wrapper
│   └── llm_client.py          # LLM backend abstraction
├── database/
│   └── db.py                  # SQLite / PostgreSQL setup
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env.example
```
Webhook test
---
## 🔮 Future Scope

RepoGuardian is designed to evolve into a fully autonomous repository intelligence platform. Planned future improvements include:

### 🚀 Advanced AI Features
- AI-generated unit and integration test creation
- Automatic bug reproduction from issue descriptions
- Root-cause analysis for failed CI/CD pipelines
- PR summarisation using LLMs for faster reviews

### 🌐 Multi-Platform Support
- Bitbucket and Azure DevOps integration
- Multi-repository organisation dashboards
- Cross-repository dependency tracking

### 🔐 Enhanced Security
- Real-time malware and ransomware signature detection
- Secret rotation recommendations
- Infrastructure-as-Code (IaC) security scanning
- Docker and Kubernetes vulnerability analysis

### 📊 Smarter Analytics
- Developer productivity insights
- Predictive technical debt analysis
- Repository stability forecasting using historical trends
- Team-wide quality benchmarking

### 🤝 Collaboration Integrations
- Slack, Discord, and Microsoft Teams notifications
- Jira and Trello integration for automatic ticket creation
- Email digest reports for repository health

### ☁️ Enterprise Deployment
- Kubernetes-native deployment support
- RBAC and SSO authentication
- Air-gapped enterprise installation
- Scalable distributed agent execution

### 🧠 Intelligent Learning System
- Self-improving agents based on reviewer feedback
- Personalised coding recommendations per developer
- Adaptive severity scoring based on project history
---
## 📄 License

 built for KLH Hackathon 2025.

---

*"GitHub Copilot is your coding assistant. RepoGuardian is your autonomous code guardian — catching what Copilot missed, before it reaches production."*
