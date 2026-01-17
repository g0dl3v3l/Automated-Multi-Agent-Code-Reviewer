# The Code Council: Automated Multi-Agent Review System

## 🚀 Project Overview

**The Code Council** is an automated "War Room" for code quality. Unlike standard linters that simply flag syntax errors, this system deploys a **Multi-Agent Architecture** where specialized AI personas critique code from distinct, conflicting perspectives:

- [cite_start]**Agent A (The Security Hawk):** Ruthlessly hunts for vulnerabilities (SQLi, CVEs)[cite: 135].
- [cite_start]**Agent B (The Speed Demon):** Obsesses over Big-O complexity and performance bottlenecks[cite: 296].
- [cite_start]**Agent C (The Clean Code Purist):** Enforces readability, naming conventions, and maintainability[cite: 349].

[cite_start]A final **"Judge" Agent** synthesizes these conflicts into a single, actionable review[cite: 416].

## 🏗️ Architecture (Fan-Out / Fan-In)

The system follows a "Map-Reduce" pattern orchestrated by **LangGraph**:

1.  **Input:** User uploads code + `requirements.txt` via **Streamlit**.
2.  **Fan-Out:** The **Flask** backend triggers Agents A, B, and C in parallel.
3.  [cite_start]**Analysis:** Agents use specialized tools (`bandit`, `radon`, `safety`) and **Mistral AI** to generate findings[cite: 660, 661].
4.  **Fan-In:** The Judge Agent deduplicates and scores the feedback.
5.  [cite_start]**Output:** A visual dashboard displays the "War Room" verdict[cite: 660].

## 🛠️ Tech Stack

- [cite_start]**Frontend:** Streamlit [cite: 660]
- [cite_start]**Backend:** Flask [cite: 660]
- [cite_start]**Orchestration:** LangGraph [cite: 660]
- [cite_start]**AI Model:** Mistral AI (`codestral-latest`) [cite: 660]
- [cite_start]**Security Tools:** `safety`, `bandit` [cite: 661]
- [cite_start]**Quality Tools:** `radon`, `pylint`, `pydocstyle` [cite: 661]

## ⚡ Setup & Installation

### Prerequisites

- Anaconda or Miniconda installed.
- Mistral AI API Key.

### 1. Create Environment

```bash
conda create -n code_reviewer python=3.10
conda activate code_reviewer
```
