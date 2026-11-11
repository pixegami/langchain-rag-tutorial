import argparse
from dotenv import load_dotenv
from symbolic_link_data import link_entities


def main():
    load_dotenv()

    parser = argparse.ArgumentParser()
    parser.add_argument("query_text", type=str, help="The query text.")
    args = parser.parse_args()
    query_text = args.query_text

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

if __name__ == "__main__":
    main()