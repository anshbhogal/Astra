import uuid
from typing import List
from engine.models.test_spec import TestSpecification, TestType
from app.models.domain import TestCase, TestSuite


class TestCompiler:
    """Compiles framework-independent TestSpecification objects into database TestCase ORM entities."""

    @classmethod
    def compile_specifications(cls, suite_id: uuid.UUID, specs: List[TestSpecification]) -> List[TestCase]:
        test_cases: List[TestCase] = []

        for spec in specs:
            ep_id = None
            if spec.endpoint_id:
                try:
                    ep_id = uuid.UUID(spec.endpoint_id)
                except ValueError:
                    ep_id = None

            t_type = spec.test_type if isinstance(spec.test_type, TestType) else TestType(spec.test_type)

            tc = TestCase(
                suite_id=suite_id,
                endpoint_id=ep_id,
                name=spec.name,
                test_type=t_type,
                execution_order=spec.execution_order,
                specification=spec.to_dict(),
                depends_on=spec.metadata.get("depends_on", [])
            )
            test_cases.append(tc)

        return test_cases
