"""Behavioural contract for structured agent-review evidence."""

from __future__ import annotations

import json

import pytest

from scripts import check_agent_review_outcome


def _classify(payload: dict[str, object], capsys: pytest.CaptureFixture[str]) -> str:
    check_agent_review_outcome.main([json.dumps(payload), "--classify"])
    return capsys.readouterr().out


def test_blocking_without_findings_is_invalid(capsys: pytest.CaptureFixture[str]) -> None:
    assert "valid=false" in _classify({"outcome": "blocking"}, capsys)


def test_rework_without_findings_is_invalid(capsys: pytest.CaptureFixture[str]) -> None:
    assert "valid=false" in _classify({"outcome": "rework"}, capsys)


def test_rework_cannot_hide_a_blocking_finding(capsys: pytest.CaptureFixture[str]) -> None:
    assert "valid=false" in _classify(
        {
            "outcome": "rework",
            "findings": [
                {
                    "severity": "blocking",
                    "confidence": "high",
                    "summary": "A blocking finding must block the required check.",
                }
            ],
        },
        capsys,
    )


def test_blocking_requires_a_blocking_finding(capsys: pytest.CaptureFixture[str]) -> None:
    assert "valid=false" in _classify(
        {
            "outcome": "blocking",
            "findings": [
                {
                    "severity": "should-fix",
                    "confidence": "high",
                    "summary": "Lower-severity feedback cannot request changes.",
                }
            ],
        },
        capsys,
    )


def test_clean_requires_no_findings(capsys: pytest.CaptureFixture[str]) -> None:
    assert "valid=false" in _classify(
        {
            "outcome": "clean",
            "findings": [
                {
                    "severity": "should-fix",
                    "confidence": "high",
                    "summary": "A clean review cannot carry a finding.",
                }
            ],
        },
        capsys,
    )


def test_valid_blocking_finding_is_reported_with_head_sha(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))

    check_agent_review_outcome.main(
        [
            json.dumps(
                {
                    "outcome": "blocking",
                    "findings": [
                        {
                            "severity": "blocking",
                            "confidence": "high",
                            "summary": "The required review result has no inspectable finding.",
                        }
                    ],
                }
            ),
            "--publish-summary",
            "--reviewed-head-sha",
            "a" * 40,
        ]
    )

    assert "a" * 40 in summary.read_text(encoding="utf-8")
    assert "BLOCKING" in summary.read_text(encoding="utf-8")
    assert "The required review result has no inspectable finding." in summary.read_text(
        encoding="utf-8"
    )


def test_findings_are_grouped_by_severity_regardless_of_payload_order(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))

    check_agent_review_outcome.main(
        [
            json.dumps(
                {
                    "outcome": "blocking",
                    "findings": [
                        {"severity": "nice-to-have", "confidence": "low", "summary": "style nit"},
                        {"severity": "blocking", "confidence": "high", "summary": "the real bug"},
                        {
                            "severity": "should-fix",
                            "confidence": "medium",
                            "summary": "worth fixing",
                        },
                    ],
                }
            ),
            "--publish-summary",
            "--reviewed-head-sha",
            "a" * 40,
        ]
    )

    text = summary.read_text(encoding="utf-8")
    assert text.index("the real bug") < text.index("worth fixing") < text.index("style nit")


def test_fallback_findings_are_posted_to_the_pr(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_run_gh(args: list[str]) -> str:
        calls.append(args)
        if "--paginate" in args:
            return "[[]]"
        return "{}"

    monkeypatch.setattr(check_agent_review_outcome, "run_gh", fake_run_gh, raising=False)

    check_agent_review_outcome.main(
        [
            json.dumps(
                {
                    "outcome": "rework",
                    "findings": [
                        {
                            "severity": "should-fix",
                            "confidence": "high",
                            "summary": "A real edge case in the drift-gate fix.",
                        }
                    ],
                }
            ),
            "--publish-pr-comment",
            "--reviewed-head-sha",
            "a" * 40,
            "--repo",
            "owner/repo",
            "--pr",
            "42",
        ]
    )

    assert len(calls) == 2
    list_call, post_call = calls
    assert "repos/owner/repo/issues/42/comments" in list_call
    assert "--method" in post_call and "POST" in post_call
    body_arg = post_call[post_call.index("-f") + 1]
    assert body_arg.startswith("body=")
    assert "a" * 40 in body_arg
    assert "NON-BLOCKING" in body_arg
    assert "A real edge case in the drift-gate fix." in body_arg


def test_clean_outcome_still_posts_a_no_findings_comment(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_run_gh(args: list[str]) -> str:
        calls.append(args)
        if "--paginate" in args:
            return "[[]]"
        return "{}"

    monkeypatch.setattr(check_agent_review_outcome, "run_gh", fake_run_gh, raising=False)

    check_agent_review_outcome.main(
        [
            json.dumps({"outcome": "clean", "findings": []}),
            "--publish-pr-comment",
            "--reviewed-head-sha",
            "e" * 40,
            "--repo",
            "owner/repo",
            "--pr",
            "42",
        ]
    )

    assert len(calls) == 2
    post_call = calls[1]
    assert "--method" in post_call and "POST" in post_call
    body_arg = post_call[post_call.index("-f") + 1]
    assert "No findings." in body_arg


def test_rerun_on_the_same_head_does_not_duplicate(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []
    sha = "b" * 40
    existing_body = f"<!-- agent-review-claude-fallback -->\nReviewed head SHA: `{sha}`\n"

    def fake_run_gh(args: list[str]) -> str:
        calls.append(args)
        if "--paginate" in args:
            return json.dumps([[{"id": 1, "body": existing_body}]])
        raise AssertionError("must not write to the PR when the reviewed head is unchanged")

    monkeypatch.setattr(check_agent_review_outcome, "run_gh", fake_run_gh, raising=False)

    check_agent_review_outcome.main(
        [
            json.dumps({"outcome": "clean", "findings": []}),
            "--publish-pr-comment",
            "--reviewed-head-sha",
            sha,
            "--repo",
            "owner/repo",
            "--pr",
            "42",
        ]
    )

    assert len(calls) == 1


def test_a_new_head_updates_the_existing_comment(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []
    old_sha = "c" * 40
    new_sha = "d" * 40
    existing_body = f"<!-- agent-review-claude-fallback -->\nReviewed head SHA: `{old_sha}`\n"

    def fake_run_gh(args: list[str]) -> str:
        calls.append(args)
        if "--paginate" in args:
            return json.dumps([[{"id": 7, "body": existing_body}]])
        return "{}"

    monkeypatch.setattr(check_agent_review_outcome, "run_gh", fake_run_gh, raising=False)

    check_agent_review_outcome.main(
        [
            json.dumps({"outcome": "clean", "findings": []}),
            "--publish-pr-comment",
            "--reviewed-head-sha",
            new_sha,
            "--repo",
            "owner/repo",
            "--pr",
            "42",
        ]
    )

    assert len(calls) == 2
    patch_call = calls[1]
    assert "--method" in patch_call and "PATCH" in patch_call
    assert "repos/owner/repo/issues/comments/7" in patch_call
    body_arg = patch_call[patch_call.index("-f") + 1]
    assert new_sha in body_arg


def _execution_file(tmp_path, messages: list[object]) -> str:
    path = tmp_path / "claude-execution-output.json"
    path.write_text(json.dumps(messages), encoding="utf-8")
    return str(path)


def _diagnose(path: str, capsys: pytest.CaptureFixture[str]) -> tuple[int | None, str, str]:
    with pytest.raises(SystemExit) as excinfo:
        check_agent_review_outcome.main(["--diagnose-execution-file", path])
    captured = capsys.readouterr()
    return excinfo.value.code, captured.out, captured.err


def test_diagnose_execution_file_reports_only_allowlisted_provider_status(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = _execution_file(
        tmp_path,
        [
            {"type": "system", "subtype": "init", "model": "claude-sonnet-5"},
            {
                "type": "assistant",
                "message": {
                    "content": [{"type": "tool_use", "name": "Bash", "input": {"command": "ls"}}]
                },
            },
            {
                "type": "result",
                "subtype": "success",
                "is_error": True,
                "duration_ms": 472,
                "num_turns": 1,
                "result": "Invalid API key provided. (401 Unauthorized)",
                "errors": ["authentication_error"],
            },
        ],
    )

    code, out, err = _diagnose(path, capsys)

    assert code == 1
    combined = out + err
    assert "auth_or_account" in combined
    assert '"subtype": "success"' in combined
    assert '"duration_ms": 472' in combined
    assert '"num_turns": 1' in combined
    assert "tool_use" not in combined
    assert "Bash" not in combined
    assert "claude-sonnet-5" not in combined


def test_diagnose_execution_file_never_echoes_raw_result_or_errors_text(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    secret = "sk-ant-api03-FAKESECRETVALUE1234567890"  # pragma: allowlist secret
    path = _execution_file(
        tmp_path,
        [
            {
                "type": "result",
                "subtype": "success",
                "is_error": True,
                "duration_ms": 900,
                "num_turns": 1,
                "result": f"401 Unauthorized: token rejected, credential={secret}",
                "errors": [f"authentication failed for {secret}"],
            }
        ],
    )

    code, out, err = _diagnose(path, capsys)

    assert code == 1
    combined = out + err
    assert secret not in combined
    assert "auth_or_account" in combined


@pytest.mark.parametrize(
    ("result_text", "errors", "is_error", "structured_output", "expected_status"),
    [
        ("401 Unauthorized: invalid api key", [], True, None, "auth_or_account"),
        ("429 Too Many Requests: rate limit exceeded", [], True, None, "rate_limited"),
        (None, ["529 Overloaded: the server is overloaded"], True, None, "overloaded"),
        ("Some completely unrecognized failure text", [], True, None, "unknown_provider_error"),
        (None, [], False, None, "schema_violation"),
    ],
)
def test_diagnose_execution_file_maps_known_patterns_to_a_closed_status_enum(
    tmp_path,
    capsys: pytest.CaptureFixture[str],
    result_text: str | None,
    errors: list[str],
    is_error: bool,
    structured_output: object,
    expected_status: str,
) -> None:
    message: dict[str, object] = {
        "type": "result",
        "subtype": "success",
        "is_error": is_error,
        "duration_ms": 100,
        "num_turns": 1,
        "errors": errors,
    }
    if result_text is not None:
        message["result"] = result_text
    if structured_output is not None:
        message["structured_output"] = structured_output
    path = _execution_file(tmp_path, [message])

    code, out, err = _diagnose(path, capsys)

    assert code == 1
    assert expected_status in (out + err)


def test_diagnose_execution_file_missing_or_malformed_stays_actionable_and_red(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    missing_path = str(tmp_path / "does-not-exist.json")
    code, out, err = _diagnose(missing_path, capsys)
    assert code == 1
    assert "execution file" in (out + err).lower()

    malformed_path = tmp_path / "malformed.json"
    malformed_path.write_text("{not valid json", encoding="utf-8")
    code, out, err = _diagnose(str(malformed_path), capsys)
    assert code == 1
    assert "execution file" in (out + err).lower()

    not_a_list_path = _execution_file(tmp_path, {})  # type: ignore[arg-type]
    code, out, err = _diagnose(not_a_list_path, capsys)
    assert code == 1
    assert "execution file" in (out + err).lower()

    no_result_path = _execution_file(tmp_path, [{"type": "system", "subtype": "init"}])
    code, out, err = _diagnose(no_result_path, capsys)
    assert code == 1
    assert "execution file" in (out + err).lower()
