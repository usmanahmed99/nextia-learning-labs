"""Opt-in: a live judge (Ollama or your own key) scores 3 replies, inside the usage cap. Skipped unless you
run `pytest -m live` with JUDGE_PROVIDER=openai_compatible and JUDGE_BASE_URL (and JUDGE_MODEL) in .env."""

import os

import pytest

pytestmark = pytest.mark.live


@pytest.fixture(autouse=True)
def mock_provider():  # replaces conftest's fixture: this test must reach the live provider
    os.environ["PYTEST_LIVE"] = "1"
    yield
    os.environ.pop("PYTEST_LIVE", None)


def test_live_judge_within_the_cap():
    from harness.config import Settings, make_provider
    from harness.dataset import load_cases
    from harness.judge import parse_verdict, reference_request
    from harness.providers import CappedProvider
    from harness.run import find_run, load_outputs

    settings = Settings.from_env()
    if settings.provider != "openai_compatible":
        pytest.skip("Set JUDGE_PROVIDER=openai_compatible to run the live test.")
    provider = make_provider(settings)
    assert isinstance(provider, CappedProvider)
    outputs = load_outputs(find_run("baseline"))
    for case in load_cases(split="dev")[:3]:
        out = outputs[case.case_id]
        verdict = parse_verdict(provider.complete(reference_request(case, out.reply, out.answer["needs_human"],
                                                                     settings.judge_model)))
        assert verdict.score in (1, 2, 3, 4, 5) or verdict.problem
    assert provider.calls == 3
