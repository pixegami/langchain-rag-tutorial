import pytest
from dotenv import load_dotenv
from neo4j_graphdb import GraphRepository
load_dotenv()

@pytest.fixture
def graph():
    repository = GraphRepository()
    yield repository
    repository.close()

def test_neo4j_connection(graph):
    print("\nVerifying Neo4j connection...")
    graph.verify_connection()
    print("Successfully connected to Neo4j!")

def test_create_constraints(graph):
    print("\nCreating database constraints...")
    graph.create_constraints()
    print("Database constraints created successfully.")
