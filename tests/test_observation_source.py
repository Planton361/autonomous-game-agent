import inspect

import pytest

import fh_agent.observation.source as observation_source_module
from fh_agent.observation.schemas import Observation
from fh_agent.observation.source import (
    ObservationSource,
    ObservationSourceExhausted,
    SequenceObservationSource,
)


def observation(observation_id: str) -> Observation:
    return Observation(
        observation_id=observation_id,
        run_id="run-1",
        ui_state="field",
        evidence_ids=[f"evidence-{observation_id}"],
    )


def test_sequence_source_returns_first_supplied_observation() -> None:
    first = observation("first")

    assert SequenceObservationSource([first]).observe() is first


def test_sequence_source_returns_supplied_observations_in_order() -> None:
    first = observation("first")
    second = observation("second")
    third = observation("third")
    source = SequenceObservationSource([first, second, third])

    assert [source.observe(), source.observe(), source.observe()] == [first, second, third]


def test_sequence_source_returns_exact_supplied_instances() -> None:
    first = observation("first")
    second = observation("second")
    source = SequenceObservationSource([first, second])

    assert source.observe() is first
    assert source.observe() is second


def test_each_successful_observe_call_advances_once() -> None:
    first = observation("first")
    second = observation("second")
    source = SequenceObservationSource([first, second])

    source.observe()
    assert source.observe() is second


def test_empty_sequence_source_raises_explicit_exhaustion() -> None:
    source = SequenceObservationSource([])

    with pytest.raises(ObservationSourceExhausted):
        source.observe()


def test_sequence_source_raises_after_final_observation() -> None:
    source = SequenceObservationSource([observation("only")])

    source.observe()

    with pytest.raises(ObservationSourceExhausted):
        source.observe()


def test_sequence_source_repeatedly_raises_after_exhaustion() -> None:
    source = SequenceObservationSource([])

    for _ in range(2):
        with pytest.raises(ObservationSourceExhausted):
            source.observe()


def test_sequence_source_snapshots_input_sequence() -> None:
    first = observation("first")
    second = observation("second")
    supplied = [first]
    source = SequenceObservationSource(supplied)
    supplied.append(second)

    assert source.observe() is first
    with pytest.raises(ObservationSourceExhausted):
        source.observe()


def test_sequence_source_does_not_mutate_observations() -> None:
    supplied = observation("unchanged")
    original = supplied.model_dump()

    assert SequenceObservationSource([supplied]).observe() is supplied
    assert supplied.model_dump() == original


def test_sequence_source_accepts_tuple_input() -> None:
    supplied = observation("tuple")

    assert SequenceObservationSource((supplied,)).observe() is supplied


def test_structurally_compatible_fake_satisfies_observation_source() -> None:
    supplied = observation("fake")

    class FakeSource:
        def observe(self) -> Observation:
            return supplied

    def consume(source: ObservationSource) -> Observation:
        return source.observe()

    assert consume(FakeSource()) is supplied


def test_source_has_no_body_manager_input_or_game_imports() -> None:
    source = inspect.getsource(observation_source_module)

    assert "fh_agent.body" not in source
    assert "fh_agent.manager" not in source
    assert "InputExecutor" not in source
    assert "fh_agent.game" not in source


def test_source_has_no_bridge_or_screen_capture_dependency() -> None:
    source = inspect.getsource(observation_source_module)

    assert "fh_agent.bridge" not in source
    assert "ScreenCapture" not in source
    assert ".capture(" not in source


def test_source_has_no_hidden_state_api() -> None:
    source = inspect.getsource(observation_source_module).lower()

    assert "hidden" not in source
    assert "memory" not in source
    assert "process" not in source


def test_source_has_no_reward_or_verifier_dependency() -> None:
    source = inspect.getsource(observation_source_module).lower()

    assert "reward" not in source
    assert "verifier" not in source


def test_equivalent_sequences_produce_equivalent_observation_order() -> None:
    first = observation("first")
    second = observation("second")
    left = SequenceObservationSource([first, second])
    right = SequenceObservationSource((first, second))

    assert [left.observe(), left.observe()] == [right.observe(), right.observe()]
