import pytest
from app.services.graph_service import graph_service


def test_graph_health(client):
    response = client.get("/api/v1/graph/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("connected", "unavailable")


def test_graph_sync_and_stats(client, db, auth_headers):
    # Test sync endpoint with authenticated user
    response = client.post(
        "/api/v1/graph/sync",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("success", "skipped")

    # Test stats endpoint
    stats_response = client.get("/api/v1/graph/stats")
    assert stats_response.status_code == 200
    stats = stats_response.json()
    assert stats["status"] in ("connected", "unavailable")


def test_neo4j_crud_and_traversal(client):
    """
    Step 2 Diagnostic:
    1. Connect to Neo4j.
    2. Create a test User node.
    3. Create Interest and Community nodes.
    4. Create relationships between them.
    5. Query the graph.
    6. Update graph relationships.
    7. Verify graph scoring.
    8. Clean up test nodes.
    """
    driver = graph_service.get_driver()
    if not driver:
        pytest.skip("Neo4j driver unavailable in current environment.")

    with driver.session() as session:
        # Cleanup any previous diagnostic run
        session.run("MATCH (n:_DiagnosticTest) DETACH DELETE n")

        # 1. Create test nodes & relationships
        create_query = (
            "CREATE (u:User:_DiagnosticTest {id: 999001, name: 'Diag User', email: 'diag@align.local'}) "
            "CREATE (c:Community:_DiagnosticTest {id: 999002, name: 'Diag Community', category: 'Technology'}) "
            "CREATE (i:Interest:_DiagnosticTest {name: 'quantum computing'}) "
            "CREATE (u)-[:HAS_INTEREST]->(i) "
            "CREATE (c)-[:HAS_TAG]->(i) "
            "CREATE (u)-[:MEMBER_OF {role: 'member'}]->(c)"
        )
        session.run(create_query)

        # 2. Query the graph
        match_query = (
            "MATCH (u:User:_DiagnosticTest {id: 999001})-[r:MEMBER_OF]->(c:Community:_DiagnosticTest {id: 999002}) "
            "RETURN u.name AS user_name, c.name AS comm_name, r.role AS role"
        )
        res = session.run(match_query).single()
        assert res is not None
        assert res["user_name"] == "Diag User"
        assert res["comm_name"] == "Diag Community"
        assert res["role"] == "member"

        # 3. Update graph relationship
        session.run(
            "MATCH (u:User:_DiagnosticTest {id: 999001})-[r:MEMBER_OF]->(c:Community:_DiagnosticTest {id: 999002}) "
            "SET r.role = 'lead_organizer'"
        )
        upd = session.run(match_query).single()
        assert upd["role"] == "lead_organizer"

        # 4. Verify affinity query using graph service
        score = graph_service.get_community_graph_score(999001, 999002)
        assert score > 0.0

        # 5. Clean up test nodes
        session.run("MATCH (n:_DiagnosticTest) DETACH DELETE n")


def test_graph_affinity_endpoints(client, auth_headers):
    # Test community affinity endpoint
    res_comm = client.get("/api/v1/graph/affinity/community/1", headers=auth_headers)
    assert res_comm.status_code == 200
    assert "graph_affinity_score" in res_comm.json()

    # Test peer affinity endpoint
    res_peer = client.get("/api/v1/graph/affinity/peer/2", headers=auth_headers)
    assert res_peer.status_code == 200
    assert "graph_affinity_score" in res_peer.json()
