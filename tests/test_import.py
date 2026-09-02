import subprocess
import sys

import pytest


def test_package_imports() -> None:
    import fh_agent

    assert fh_agent.__version__


@pytest.mark.parametrize(
    "imports",
    [
        "import fh_agent.memory.evidence\nimport fh_agent.perception.offline_processor",
        "import fh_agent.perception.offline_processor\nimport fh_agent.memory.evidence",
    ],
)
def test_evidence_and_offline_processor_import_in_either_order(imports: str) -> None:
    result = subprocess.run(
        [sys.executable, "-c", imports],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    "imports",
    [
        "import fh_agent.observation.observation_builder\nimport fh_agent.perception.ocr",
        "import fh_agent.perception.ocr\nimport fh_agent.observation.observation_builder",
        (
            "import fh_agent.observation.observation_builder\n"
            "import fh_agent.perception.offline_processor"
        ),
        (
            "from fh_agent.perception import observation_to_json, process_saved_frame\n"
            "assert callable(observation_to_json)\n"
            "assert callable(process_saved_frame)"
        ),
        (
            "import sys\n"
            "import fh_agent.perception.ocr\n"
            "assert 'fh_agent.perception.offline_processor' not in sys.modules"
        ),
    ],
)
def test_perception_imports_are_order_independent(imports: str) -> None:
    result = subprocess.run(
        [sys.executable, "-c", imports],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
