import argparse
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

from neo4j_graphdb import GraphRepository
from query_data import PROMPT_TEMPLATE
from symbolic_link_data import link_entities, to_senses


def main():
    load_dotenv()

    parser = argparse.ArgumentParser()
    parser.add_argument("query_text", type=str, help="The query text.")
    args = parser.parse_args()
    query_text = args.query_text

    # Link the query's entities to synsets, the same way chunks were linked in symbolic_link_data.py.
    senses = to_senses(link_entities(query_text))
    print(f"Query synsets: {[(s['surface'], s['synset_id']) for s in senses]}")
    synset_ids = list(dict.fromkeys(s["synset_id"] for s in senses))

    # Find every chunk mentioning one of those synsets (exact match), most matched synsets first.
    results = []
    if synset_ids:
        graph = GraphRepository()
        try:
            results = graph.find_chunks_by_synset_ids(synset_ids)
        finally:
            graph.close()
    if len(results) == 0:
        print(f"Unable to find matching results.")
        return

    context_text = "\n\n---\n\n".join([chunk["text"] for chunk in results])
    prompt_template = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
    prompt = prompt_template.format(context=context_text, question=query_text)
    print(prompt)

    model = ChatOpenAI(model="gpt-4.1-mini", temperature=0)
    response = model.invoke(prompt)
    response_text = response.content

    sources = [f"{chunk['source']} ({chunk['chunk_id']})" for chunk in results]
    formatted_response = f"Response: {response_text}\nSources: {sources}"
    print(formatted_response)


if __name__ == "__main__":
    main()
