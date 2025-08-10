# Agentic RAG with LangChain

This project demonstrates how to build an Agentic Retrieval-Augmented Generation (RAG) pipeline using LangChain, where an LLM-powered agent can decide when and how to retrieve information from your knowledge base, instead of blindly fetching context every time. The agent dynamically chooses retrieval, reasoning, and tool usage, allowing more efficient and context-aware responses.

## 🛠 Installation

### 1. Environment Setup
Some dependencies (like `onnxruntime`) can be tricky to install depending on your OS. Follow the steps for your platform before running `pip install`.

#### MacOS
```bash
conda install onnxruntime -c conda-forge
```
See the [onnxruntime GitHub issue](https://github.com/microsoft/onnxruntime) for extra help.

#### Windows
Follow [this guide](https://docs.microsoft.com/en-us/cpp/build/vscpp-step-by-step) to install Microsoft C++ Build Tools, making sure to set the environment variable path.

### 2. Install Requirements
```bash
pip install -r requirements.txt
```

### 3. Install Markdown Dependencies
```bash
pip install "unstructured[md]"
```

## 📂 Building the Knowledge Base
This step ingests your documents into a Chroma vector database so the agent can retrieve relevant chunks when needed.

```bash
python create_database.py
```

## 💬 Running the Agentic RAG
Instead of a simple retrieval pipeline, here the agent:
- Reads your query.
- Decides whether retrieval is needed.
- Queries Chroma DB only if relevant.
- Combines retrieved context with its own reasoning.

Example query:
```bash
python agentic_query.py "How does Alice meet the Mad Hatter?"
```

## 🔑 API Keys
You’ll need an OpenAI API key set in your environment variables:

```bash
# Mac/Linux
export OPENAI_API_KEY="your_api_key_here"

# Windows
setx OPENAI_API_KEY "your_api_key_here"
```

## 📺 Reference Tutorial
While this project is based on traditional RAG examples like [Pixegami’s LangChain RAG tutorial](https://github.com/pixegami/langchain-rag-tutorial), the code here has been adapted for Agentic RAG — allowing more intelligent, context-aware querying.

## 📜 Features of Agentic RAG vs Traditional RAG
| Feature                     | Traditional RAG         | Agentic RAG            |
|-----------------------------|-------------------------|------------------------|
| Always fetches context      | ✅ Always              | 🔄 Only when needed   |
| Reasoning before retrieval  | ❌ No                  | ✅ Yes                |
| Multi-tool orchestration    | ❌ Limited             | ✅ Yes                |
| Efficiency                  | ⚠️ Sometimes redundant | 🚀 Optimized          |