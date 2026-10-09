import pytest
import networkx as nx
from engine.regression.impact_analyzer import PKGImpactAnalyzer


def test_pkg_impact_analyzer_reachability():
    graph = nx.DiGraph()

    # Endpoint -> Handler -> Service Func
    graph.add_node("endpoint:GET:/api/v1/users", type="ENDPOINT", properties={"method": "GET", "path": "/api/v1/users"})
    graph.add_node("python:app.api.users.get_users_endpoint", type="FUNCTION")
    graph.add_node("python:app.services.user_service.UserService.get_user", type="FUNCTION")

    graph.add_edge("endpoint:GET:/api/v1/users", "python:app.api.users.get_users_endpoint", relationship="HANDLED_BY")
    graph.add_edge("python:app.api.users.get_users_endpoint", "python:app.services.user_service.UserService.get_user", relationship="CALLS")

    analyzer = PKGImpactAnalyzer(max_depth=5)
    impacted = analyzer.compute_impact(
        graph=graph,
        changed_symbols=["python:app.services.user_service.UserService.get_user"],
        changed_files=["app/services/user_service.py"],
    )

    assert len(impacted) == 1
    assert impacted[0].method == "GET"
    assert impacted[0].path == "/api/v1/users"
    assert impacted[0].impact_distance >= 0
    assert impacted[0].confidence_score > 0.5
