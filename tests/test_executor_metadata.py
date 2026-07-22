"""Regression tests for the credential-metadata leak fix in executor.py.

These verify that reserved private keys in request/message/part metadata never
reach the model-visible payload built by _payload_from_context(). Uses a sentinel
secret only — never a real credential.

executor.py degrades gracefully without a2a-sdk (its base class becomes object),
so these import and run without the SDK installed.
"""
from __future__ import annotations

import json

import pytest

from agent_skeleton.executor import _model_visible_metadata, _payload_from_context

SENTINEL = "TEST_SECRET_DO_NOT_LEAK"


def _ctx(*, metadata=None, message=None):
    return type("Ctx", (), {"metadata": metadata, "message": message})()


def _msg(*, metadata=None, parts=None):
    return type("Msg", (), {"metadata": metadata, "parts": parts or []})()


def test_helper_strips_reserved_keys_case_insensitive():
    out = _model_visible_metadata(
        {"credentials": {"api_key": SENTINEL}, "Authorization": SENTINEL, "prompt": "q"}
    )
    assert out == {"prompt": "q"}


def test_helper_handles_non_dict():
    assert _model_visible_metadata(None) == {}
    assert _model_visible_metadata("nope") == {}


def test_context_metadata_credentials_not_in_payload():
    ctx = _ctx(metadata={"credentials": {"ncbi_api_key": {"api_key": SENTINEL}}, "prompt": "q"})
    payload = _payload_from_context(ctx)
    assert "credentials" not in payload
    assert SENTINEL not in json.dumps(payload)
    assert payload["prompt"] == "q"


def test_ordinary_metadata_still_flows():
    ctx = _ctx(metadata={"prompt": "hello", "skill": "evidence-trail/build-map"})
    payload = _payload_from_context(ctx)
    assert payload["prompt"] == "hello"
    assert payload["skill"] == "evidence-trail/build-map"


def test_message_and_datapart_metadata_are_filtered():
    # Use the real a2a DataPart so is_data_part() recognizes it; skip if the SDK
    # is not installed (the executor still imports without it).
    a2a_types = pytest.importorskip("a2a.types")
    root = a2a_types.DataPart(
        data={"credentials": {"api_key": SENTINEL}, "topic": "obesity"},
        metadata={"secrets": SENTINEL},
    )
    part = a2a_types.Part(root=root)
    msg = _msg(metadata={"authorization": SENTINEL, "prompt": "q"}, parts=[part])
    ctx = _ctx(metadata={"credentials": SENTINEL}, message=msg)

    payload = _payload_from_context(ctx)
    assert SENTINEL not in json.dumps(payload)
    # legitimate structured input from the DataPart still survives
    assert payload.get("topic") == "obesity"
    assert payload.get("prompt") == "q"
