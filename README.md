# 🧠 Text-to-SQL GenAI System

**Natural Language → SQL → Database Insights**

A production-style Generative AI application that converts plain English questions into executable SQL queries and retrieves results from a PostgreSQL database (Neon). The system includes multi-tier caching, LLM observability, cost tracking, and an interactive Streamlit dashboard.

**Live Demo:**
https://text2sql-asheeshpatel.streamlit.app/

---

## ✨ Key Features

* 🗣️ Natural language to SQL using an LLM
* 🗄️ PostgreSQL (Neon) backend
* ⚡ Multi-tier caching

  * Tier-1: In-memory cache
  * Tier-2: Persistent DB cache
*  Real-time token usage & cost estimation
*  Schema-aware SQL generation
*  LLM observability with Langfuse
*  Safe SQL validation (SELECT-only)
*  Interactive Streamlit dashboard
* Query history + CSV download
* Docker support for local deployment

---

##Architecture Overview

```
User → Streamlit UI → LLM (Text-to-SQL)
                     ↓
                SQL Query
                     ↓
              PostgreSQL (Neon)
                     ↓
                 Result Table
```

Enhancements:

* Cache layer reduces latency & cost
* Observability tracks tokens, latency, errors
* Schema introspection improves accuracy

---

## 📦 Tech Stack

* **Python 3.13.5**
* Streamlit
* LangChain
* OpenAI API
* PostgreSQL (Neon)
* SQLAlchemy
* Pandas
* Langfuse (Observability)
* Docker

---

## 🚀 Run the App Locally (From GitHub)

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/<your-username>/Text2SQL.git
cd Text2SQL
```

---

### 2️⃣ Create a Virtual Environment

```bash
python -m venv .venv
```

Activate:

**Windows**

```bash
.venv\Scripts\activate
```

**macOS / Linux**

```bash
source .venv/bin/activate
```

---

### 3️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

---

### 4️⃣ Configure Environment Variables

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=your_openai_key
NEON_DB_URL=postgresql://user:password@host/db?sslmode=require
LANGFUSE_PUBLIC_KEY=pk-xxxx
LANGFUSE_SECRET_KEY=sk-xxxx
LANGFUSE_HOST=https://cloud.langfuse.com
```

---

### 5️⃣ Run the Streamlit App

```bash
streamlit run app/app.py
```

Open in browser:

```
http://localhost:8501
```

---

## 🐳 Run Using Docker

### Build Image

```bash
docker build -t text2sql .
```

---

### Run Container

```bash
docker run -p 8501:8501 --env-file .env text2sql
```

Then open:

```
http://localhost:8501
```

---

## 🌐 Access the Hosted Version

You can use the deployed app directly:

👉 https://text2sql-asheeshpatel.streamlit.app/

---

## 📊 How It Works

1. User enters a natural language query
2. System retrieves database schema
3. LLM generates safe SQL query
4. Query executes on PostgreSQL
5. Results displayed in table form
6. Cache stores results for future reuse
7. Observability logs usage metrics

---

## ⚡ Caching Strategy

### Tier-1 Cache (Memory)

* Fastest access
* Session-level reuse
* Zero database calls

### Tier-2 Cache (Persistent)

* Stored in PostgreSQL
* Cross-session reuse
* Reduces LLM cost

---

## 🔍 Observability & Monitoring

Langfuse integration provides:

* Token usage tracking
* Latency measurement
* Cost estimation
* Prompt logging
* Error tracing

---

## 📁 Project Structure

```
Text2SQL/
│
├── app/                # Streamlit UI
├── llm/                # Text-to-SQL logic
├── db/                 # Database utilities
├── cache/              # Multi-tier caching
├── observability/      # Langfuse integration
│
├── requirements.txt
├── Dockerfile
├── .env.example
└── README.md
```

---

## 🛡️ Safety Measures

* Only SELECT queries allowed
* SQL validation before execution
* No destructive operations permitted
* Schema-constrained generation

---

## 📌 Notes

* Requires valid OpenAI API key
* Requires accessible PostgreSQL database
* Designed for portfolio and production-style demonstrations

---

## 🔜 What Can Be Done Next

* **Semantic cache lookup** — Introduce embedding-based similarity so equivalent questions reuse the same cached SQL. For instance, “How many users signed up last month?” and “What’s the count of new signups in the previous month?” would both resolve to one cached query, avoiding duplicate LLM calls and lowering latency and cost.

---

⭐ If you find this project useful, consider giving it a star!
