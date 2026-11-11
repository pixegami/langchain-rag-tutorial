import argparse
import json
from dotenv import load_dotenv

# from dataclasses import dataclass
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from symbolic_link_data import link_entities


# PROMPT_TEMPLATE = """
# Answer the question based only on the following context:

# {context}

# ---

# Answer the question based on the above context: {question}
# """


def main():
    load_dotenv()
    # Create CLI.
    parser = argparse.ArgumentParser()
    parser.add_argument("query_text", type=str, help="The query text.")
    args = parser.parse_args()
    query_text = args.query_text

    # Prepare the DB.
    results = link_entities(query_text)
   
    if isinstance(results, dict) and results:
        context = {
            "sentence": results.get("sentence", ""),
            "entities": results.get("entities", "")
        }
        print(context)
        return context
    else:
        return {}
    # if len(context.entities) == 0:
    #     print(f"Unable to find matching results from wsd entity linker.")
    #     return

    # context_text = "\n\n---\n\n".join([doc.page_content for doc, _score in results])
    # prompt_template = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
    # prompt = prompt_template.format(context=context_text, question=query_text)
    # print(prompt)

    # model = ChatOpenAI(model="gpt-4.1-mini", temperature=0)
    # response = model.invoke(prompt)
    # response_text = response.content

    # sources = [doc.metadata.get("source", None) for doc, _score in results]
    # formatted_response = f"Response: {response_text}\nSources: {sources}"
    # print(formatted_response)


if __name__ == "__main__":
    main()
