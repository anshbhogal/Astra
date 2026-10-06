from engine.analyzer.models.endpoint import APIEndpoint, APIParameter
from engine.generator.suite_generator import SyntheticTestSuiteGenerator
from engine.models.test_spec import TestType


def test_synthetic_suite_generator():
    ep = APIEndpoint(
        method="POST",
        path="/users/{user_id}",
        function_name="create_user_item",
        qualified_function_name="main.create_user_item",
        parameters=[
            APIParameter(name="user_id", type="int", required=True, location="path"),
            APIParameter(name="email", type="str", required=True, location="body")
        ],
        response_model="dict",
        file_path="main.py",
        line_number=14,
        framework="PYTHON_FASTAPI",
        confidence=0.98
    )

    generator = SyntheticTestSuiteGenerator()
    specs = generator.generate_suite_for_endpoints([ep])

    assert len(specs) == 4
    test_types = [s.test_type for s in specs]
    assert TestType.HAPPY_PATH in test_types
    assert TestType.MISSING_REQUIRED in test_types
    assert TestType.INVALID_TYPE in test_types
    assert TestType.UNAUTHORIZED in test_types

    happy_spec = next(s for s in specs if s.test_type == TestType.HAPPY_PATH)
    assert happy_spec.method == "POST"
    assert happy_spec.path == "/users/{user_id}"
    assert happy_spec.path_params == {"user_id": 1}
    assert happy_spec.body == {"email": "test@astra.local"}
