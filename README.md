# Knowledge Base Chatbot

A simple chatbot that can answer questions based on a knowledge base of markdown documents using Retrieval Augmented Generation (RAG).

## Features

- FastAPI backend with token-based authentication
- Streamlit frontend for easy interaction
- LangChain + OpenAI for RAG implementation
- Vector storage using Chroma
- Rate limiting for API protection

## Setup

### Prerequisites

- Python 3.9+
- OpenAI API key
- Markdown files for training data

### Installation

1. Clone the repository:
   ```
   git clone <repository-url>
   cd <repository-directory>
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Create a `.env` file based on the template:
   ```
   cp .env.template .env
   ```

4. Edit the `.env` file to add your OpenAI API key and other settings.

### Training the Bot

1. Place your markdown (.md) files in the `data/prototype` directory.

2. Run the training script:
   ```
   python train.py
   ```
   
   This will process all markdown files and create a vector database in the `chroma` directory.

### Running the API Server

1. Start the FastAPI server:
   ```
   python run.py
   ```

   The API will be available at `http://localhost:8000`.

### Using the Chat UI

1. Start the Streamlit UI:
   ```
   streamlit run client/chat_ui.py
   ```

2. Open your browser at `http://localhost:8501`.

3. Enter your API secret key in the sidebar.

4. Start chatting with the bot!

## API Endpoints

### GET /docs
OpenAPI documentation for the API.

### POST /get_token/
Get a one-time token for authentication.

Request body:
```json
{
  "secret": "your_secret_key_here"
}
```

Response:
```json
{
  "token": "uuid-token-here"
}
```

### POST /chat
Send a question to the chatbot.

Request body:
```json
{
  "question": "Your question here?",
  "token": "your-one-time-token"
}
```

Response:
```json
{
  "answer": "The answer based on knowledge base."
}
```

## Project Structure

```
.
├── client
│   └── chat_ui.py
├── config
│   ├── config.py
│   └── logging_config.py
├── run.py
├── src
│   ├── main.py
│   ├── query_data.py
│   ├── rag.py
│   └── security.py
└── train
    ├── __pycache__
    │   └── create_database.cpython-39.pyc
    ├── compare_embeddings.py
    ├── create_database.py
    ├── data
    │   ├── books
    │   │   └── alice_in_wonderland.md
    │   ├── prototype
    │   │   └── test.md
    │   └── sample_chats
    │       └── sample_chat_cleaned.md
    └── train.py

9 directories, 15 files
```

## License

[Your License Here]

## Credits

- [OpenAI](https://openai.com/)
- [LangChain](https://langchain.com/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Streamlit](https://streamlit.io/)