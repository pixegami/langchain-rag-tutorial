#!/usr/bin/env python3
# Copied unchanged from wsd-entity-linker (TalkingDB/Symbolic-RAG-TRL3), glosstag-to-graph/glosstag_to_graph.py
# at commit b05928eec89c0872a894cbd50efa7e06b99b5098, so this repo builds the same graph. Update it from there.
"""Turn the WordNet 3.0 Princeton Gloss Corpus (glosstag) into a graph.

Reads the merged annotation files (WordNet-3.0/glosstag/merged/{noun,verb,adj,adv}.xml).
The glosstag README recommends these over the standoff files, which hold the same
annotations split over ~8,000 files. Every word or collocation in a gloss that was
sense-tagged (manually or automatically) becomes an edge from the synset that owns
the gloss to the sense it was disambiguated to:

    (:Synset)-[:GLOSS_LINKS_TO]->(:Sense)-[:IN_SYNSET]->(:Synset)

Nodes
  Synset  id (e.g. n00003553), pos, offset, terms, gloss (original WordNet text),
          definition, examples
  Sense   id = sense key (e.g. entity%1:03:00::), lemma, synset
Edges
  IN_SYNSET       Sense -> Synset it belongs to
  GLOSS_LINKS_TO  Synset -> Sense tagged in its gloss. Properties: token (glosstag id
                  of the wf/glob), text (surface form in the gloss), lemma, section
                  (def | ex), tag (man | auto | llm), kind (word | collocation), position
                  (order of the token within the gloss). A token tagged with several
                  senses yields one edge per sense.

Outputs, under --out (default glosstag-to-graph/output/):
  wordnet-glosstag.graphml  GraphML. Opens in Neo4j (apoc.import.graphml with
                            readLabels), Gephi, yEd, NetworkX, igraph, ...
  neo4j/*.csv               CSVs for `neo4j-admin database import full`.
List-valued properties (terms, examples) are joined with "|", which never occurs in
the glosses.

With --merged pointing at the output of annotate-tag-un.py, the words the corpus left
untagged (tag="un") but that carry an annotation="<sense key>" also become edges, with
tag = "llm".

With --ignore-senses pointing at the output of find_common_senses.py, GLOSS_LINKS_TO
edges to the senses marked ignore = true (very common senses that carry little meaning,
like be%2:42:03::) are left out. Their Sense nodes and IN_SYNSET edges are still written.

Usage:
    python glosstag-to-graph/glosstag_to_graph.py [--out DIR] [--merged DIR] [--ignore-senses FILE]
"""

import argparse
import csv
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

HERE = Path(__file__).resolve().parent
MERGED_DIR = HERE / "WordNet-3.0" / "glosstag" / "merged"
POS_FILES = ["noun", "verb", "adj", "adv"]

# Placeholder sense key used for tokens the annotators deliberately left untagged.
IGNORED_SK = "purposefully_ignored%0:00:00::"
LIST_SEP = "|"
# Edge `tag` for senses that annotate-tag-un.py added to tag="un" words with an LLM.
LLM_TAG = "llm"

NODE_KEYS = [  # (graphml key, attr.type)
    ("labels", "string"),
    ("pos", "string"),
    ("offset", "string"),
    ("terms", "string"),
    ("gloss", "string"),
    ("definition", "string"),
    ("examples", "string"),
    ("lemma", "string"),
    ("synset", "string"),
]
EDGE_KEYS = [
    ("label", "string"),
    ("token", "string"),
    ("text", "string"),
    ("lemma", "string"),
    ("section", "string"),
    ("tag", "string"),
    ("kind", "string"),
    ("position", "int"),
]


def detokenize(elem):
    """Rebuild readable text from the wf/cf tokens of a def or ex."""
    out = []

    def walk(e):
        for child in e:
            if child.tag in ("wf", "cf"):
                out.append("".join(child.itertext()).strip())
                out.append(child.get("sep", " "))
            elif child.tag == "qf":
                q = '"' if child.get("rend", "dq") == "dq" else "'"
                out.append(q)
                walk(child)
                if out and out[-1] == " ":
                    out.pop()
                out.append(q + " ")
            else:  # aux, mwf, classif
                walk(child)

    walk(elem)
    return "".join(out).strip().rstrip(";").strip()


def gloss_links(wsd):
    """Yield one dict per (sense-tagged token, sense key) in a wsd gloss, in order."""
    position = 0
    for section_elem in wsd:  # classif, aux, def, ex
        section = section_elem.tag
        if section not in ("def", "ex"):
            section = "def"  # aux/classif around a def; only aux type="arg" is tagged
        # Surface text of each collocation, gathered from its (possibly discontiguous) cfs.
        coll_text = {}
        for cf in section_elem.iter("cf"):
            word = "".join(cf.itertext()).strip()
            for c in cf.get("coll", "").split(","):
                coll_text.setdefault(c, []).append(word)
        for e in section_elem.iter():
            if e.tag == "wf":
                kind, text = "word", "".join(e.itertext()).strip()
            elif e.tag == "glob":
                kind, text = "collocation", " ".join(coll_text.get(e.get("coll"), []))
            else:
                continue
            position += 1
            # Untagged words sense-annotated by annotate-tag-un.py: <wf tag="un" annotation="<sk>">.
            sk = e.get("annotation")
            if sk:
                yield {
                    "token": e.get("id"),
                    "text": text,
                    "lemma": sk.split("%", 1)[0].replace("_", " "),
                    "section": section,
                    "tag": LLM_TAG,
                    "kind": kind,
                    "position": position,
                    "sense": sk,
                }
            for i in e.findall("id"):
                sk = i.get("sk")
                if not sk or sk == IGNORED_SK:
                    continue
                yield {
                    "token": e.get("id"),
                    "text": text,
                    "lemma": i.get("lemma"),
                    "section": section,
                    "tag": e.get("tag"),
                    "kind": kind,
                    "position": position,
                    "sense": sk,
                }


def sense_lemma(sk, terms):
    """Pick the synset term a sense key belongs to (keys are lower-cased, terms aren't)."""
    key_lemma = sk.split("%", 1)[0]
    for t in terms:
        if t.lower().replace(" ", "_") == key_lemma:
            return t
    return key_lemma.replace("_", " ")


def parse_synsets(path):
    for _, el in ET.iterparse(path):
        if el.tag != "synset":
            continue
        terms = [t.text for t in el.iter("term")]
        keys = [k.text for k in el.iter("sk")]
        glosses = {g.get("desc"): g for g in el.findall("gloss")}
        wsd = glosses["wsd"]
        d = wsd.find("def")
        yield {
            "id": el.get("id"),
            "pos": el.get("pos"),
            "offset": el.get("ofs"),
            "terms": terms,
            "gloss": glosses["orig"].findtext("orig", "").strip(),
            "definition": detokenize(d) if d is not None else "",
            "examples": [detokenize(ex) for ex in wsd.findall("ex")],
            "senses": [(sk, sense_lemma(sk, terms)) for sk in keys],
            "links": list(gloss_links(wsd)),
        }
        el.clear()


def graphml_data(props):
    return "".join(
        f'<data key="{k}">{escape(str(v))}</data>' for k, v in props.items() if v not in (None, "")
    )


class Writers:
    def __init__(self, out):
        neo = out / "neo4j"
        neo.mkdir(parents=True, exist_ok=True)
        self.files = []

        def csv_writer(name, header):
            f = open(neo / name, "w", newline="", encoding="utf-8")
            self.files.append(f)
            w = csv.writer(f)
            w.writerow(header)
            return w

        self.synsets = csv_writer(
            "synsets.csv",
            ["id:ID", ":LABEL", "pos", "offset", "terms:string[]", "gloss", "definition",
             "examples:string[]"],
        )
        self.senses = csv_writer("senses.csv", ["id:ID", ":LABEL", "lemma", "synset"])
        self.in_synset = csv_writer("in_synset.csv", [":START_ID", ":END_ID", ":TYPE"])
        self.links = csv_writer(
            "gloss_links_to.csv",
            [":START_ID", ":END_ID", ":TYPE", "token", "text", "lemma", "section", "tag",
             "kind", "position:int"],
        )

        # GraphML edges are written to a side file and appended after the nodes, so the
        # whole graph streams through without holding the edges in memory.
        self.graphml_path = out / "wordnet-glosstag.graphml"
        self.graphml = open(self.graphml_path, "w", encoding="utf-8")
        self.edges_path = out / ".graphml-edges.tmp"
        self.edges = open(self.edges_path, "w", encoding="utf-8")
        g = self.graphml
        g.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        g.write('<graphml xmlns="http://graphml.graphdrawing.org/xmlns">\n')
        for k, t in NODE_KEYS:
            g.write(f'<key id="{k}" for="node" attr.name="{k}" attr.type="{t}"/>\n')
        for k, t in EDGE_KEYS:
            g.write(f'<key id="{k}" for="edge" attr.name="{k}" attr.type="{t}"/>\n')
        g.write('<graph id="wordnet-glosstag" edgedefault="directed">\n')
        self.n_edges = 0

    def node(self, node_id, label, props):
        props = {"labels": f":{label}", **props}
        self.graphml.write(
            f"<node id={quoteattr(node_id)} labels={quoteattr(':' + label)}>"
            f"{graphml_data(props)}</node>\n"
        )

    def edge(self, src, dst, label, props):
        self.n_edges += 1
        props = {"label": label, **props}
        self.edges.write(
            f'<edge id="e{self.n_edges}" source={quoteattr(src)} target={quoteattr(dst)} '
            f"label={quoteattr(label)}>{graphml_data(props)}</edge>\n"
        )

    def synset(self, s):
        terms, examples = LIST_SEP.join(s["terms"]), LIST_SEP.join(s["examples"])
        self.synsets.writerow(
            [s["id"], "Synset", s["pos"], s["offset"], terms, s["gloss"], s["definition"],
             examples]
        )
        self.node(s["id"], "Synset", {
            "pos": s["pos"], "offset": s["offset"], "terms": terms, "gloss": s["gloss"],
            "definition": s["definition"], "examples": examples,
        })
        for sk, lemma in s["senses"]:
            self.senses.writerow([sk, "Sense", lemma, s["id"]])
            self.node(sk, "Sense", {"lemma": lemma, "synset": s["id"]})
            self.in_synset.writerow([sk, s["id"], "IN_SYNSET"])
            self.edge(sk, s["id"], "IN_SYNSET", {})
        for link in s["links"]:
            props = {k: link[k] for k in ("token", "text", "lemma", "section", "tag", "kind",
                                          "position")}
            self.links.writerow([s["id"], link["sense"], "GLOSS_LINKS_TO", *props.values()])
            self.edge(s["id"], link["sense"], "GLOSS_LINKS_TO", props)

    def close(self):
        for f in self.files:
            f.close()
        self.edges.close()
        with open(self.edges_path, encoding="utf-8") as edges:
            for line in edges:
                self.graphml.write(line)
        self.edges_path.unlink()
        self.graphml.write("</graph>\n</graphml>\n")
        self.graphml.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, default=HERE / "output")
    ap.add_argument("--merged", type=Path, default=MERGED_DIR,
                    help="directory with {noun,verb,adj,adv}.xml (default: the glosstag release's merged/). "
                         "Point it at merged_with_tag_un_annotated_haiku/ to add the LLM-annotated words.")
    ap.add_argument("--ignore-senses", type=Path,
                    help="JSON from find_common_senses.py; GLOSS_LINKS_TO edges to its senses with "
                         "ignore = true are left out")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    ignored = set()
    if args.ignore_senses:
        ignored = {s["sense"] for s in json.loads(args.ignore_senses.read_text()) if s["ignore"]}
        print(f"ignoring links to {len(ignored)} senses from {args.ignore_senses}")

    # Read everything first so links can be checked against the full set of sense keys.
    synsets = []
    for pos in POS_FILES:
        before = len(synsets)
        synsets.extend(parse_synsets(args.merged / f"{pos}.xml"))
        print(f"{pos}: {len(synsets) - before} synsets")
    known = {sk for s in synsets for sk, _ in s["senses"]}

    w = Writers(args.out)
    n_senses = n_links = dropped = n_ignored = 0
    for s in synsets:
        kept = [l for l in s["links"] if l["sense"] in known]
        dropped += len(s["links"]) - len(kept)
        n_ignored += sum(l["sense"] in ignored for l in kept)
        kept = [l for l in kept if l["sense"] not in ignored]
        s["links"] = kept
        n_senses += len(s["senses"])
        n_links += len(kept)
        w.synset(s)
    w.close()

    print(f"{len(synsets)} Synset, {n_senses} Sense nodes; "
          f"{n_senses} IN_SYNSET, {n_links} GLOSS_LINKS_TO edges "
          f"({dropped} links to unknown sense keys dropped, {n_ignored} links to ignored senses left out)")
    print(f"wrote {w.graphml_path} and {args.out / 'neo4j'}/")


if __name__ == "__main__":
    main()
