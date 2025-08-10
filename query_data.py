import os
import argparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY not found in .env")

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain.tools import Tool
from langchain.agents import initialize_agent, AgentType
from langchain.prompts import PromptTemplate

CHROMA_PATH = "chroma"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("query_text", type=str, help="The query text.")
    args = parser.parse_args()
    query_text = args.query_text

    # Prepare DB + retriever
    embedding_function = OpenAIEmbeddings()
    db = Chroma(
        persist_directory=CHROMA_PATH,
        embedding_function=embedding_function
    )
    retriever = db.as_retriever(search_kwargs={"k": 3})

    # Define a retrieval tool
    retrieval_tool = Tool(
        name="Document Search",
        func=lambda q: "\n".join([doc.page_content for doc in retriever.get_relevant_documents(q)]),
        description="Searches the knowledge base for relevant information to answer a question."
    )

    # LLM
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    # Agent
    agent = initialize_agent(
        tools=[retrieval_tool],
        llm=llm,
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True
    )

    # Ask the agent
    answer = agent.run(query_text)
    print("\nFinal Answer:\n", answer)

if __name__ == "__main__":
    main()
