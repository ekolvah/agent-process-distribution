"""The post-merge endpoints of the installer tests' `FakeGitHub` (change
init-runs-post-merge-steps): auth accounts, auto-merge, the PR read and body edit, the
`activate_protection` preflight, the Project role, rulesets, check runs and invitations."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from tests.publisher import init_harness as h


class PostMergeGitHub:
    """Mixed into `init_harness.FakeGitHub`, whose state these handlers read and change."""

    accounts: list[dict[str, Any]]
    allow_auto_merge: bool
    callers: bool
    check_runs: list[dict[str, Any]]
    default_branch: str
    invitations: list[dict[str, Any]]
    permissions: dict[str, str]
    project_writers: set[str]
    pulls: list[dict[str, Any]]
    rulesets: dict[int, dict[str, Any]]
    tokens: dict[str, str]

    def _post_merge(
        self, args: list[str], token: str | None
    ) -> subprocess.CompletedProcess[str] | None:
        """The calls of the post-merge steps (change init-runs-post-merge-steps), else None."""
        graphql = args[:2] == ["api", "graphql"]
        if args[0] == "auth":
            handler = self._auth
        elif args[:2] == ["repo", "edit"]:
            handler = self._auto_merge
        elif args[:2] in (["pr", "view"], ["pr", "edit"]):
            handler = self._pull
        elif graphql and "nameWithOwner" in args[-1]:
            handler = self._callers
        elif graphql and "updateProjectV2Collaborators" in args[-1]:
            handler = self._project_role
        elif args[0] == "api" and not graphql and not self._legacy_read(args):
            return self._rest(args, token)
        else:
            return None
        return handler(args)

    def _auto_merge(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        assert args[2:] == [f"{h.OWNER}/{h.REPO_NAME}", "--enable-auto-merge"], args
        self.allow_auto_merge = True
        return h._done(args)

    def _pull(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        """`gh pr view <N> --json headRefOid,baseRefName` and `gh pr edit <N> --repo R --body B`."""
        (pull,) = [p for p in self.pulls if p["number"] == int(args[2])]
        if args[1] == "view":
            assert args[3:] == ["--json", "headRefOid,baseRefName"], args
            return h._done(args, {"headRefOid": h.HEAD_SHA, "baseRefName": pull["base"]})
        assert args[3:6] == ["--repo", f"{h.OWNER}/{h.REPO_NAME}", "--body"] and len(args) == 7, (
            args
        )
        pull["body"] = args[6]
        return h._done(args, out=pull["url"] + "\n")

    def _callers(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        """The preflight read of `activate_protection`: both process callers on the default branch."""
        blob = {"__typename": "Blob"} if self.callers else None
        read = {
            "nameWithOwner": f"{h.OWNER}/{h.REPO_NAME}",
            "defaultBranchRef": {"name": self.default_branch},
        }
        return h._done(args, {"data": {"repository": {**read, "object": blob, "review": blob}}})

    def _project_role(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        fields = dict(part.split("=", 1) for part in args[3:-1:2])
        assert "role:WRITER" in args[-1] and fields["user"].startswith("U_"), args
        self.project_writers.add(fields["user"].removeprefix("U_"))
        return h._done(args, {"data": {"updateProjectV2Collaborators": {"clientMutationId": None}}})

    def _auth(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        """`gh auth status --json hosts` and `gh auth token --user <login>`."""
        if args[1] == "status":
            assert args[2:] == ["--json", "hosts"], args
            hosts = [
                {**account, "host": "github.com", "state": "success"} for account in self.accounts
            ]
            return h._done(args, {"hosts": {"github.com": hosts}})
        assert args[1:3] == ["token", "--user"] and len(args) == 4, args
        if args[3] not in self.tokens:
            return h._done(args, code=1, err=f"no oauth token found for {args[3]}\n")
        return h._done(args, out=self.tokens[args[3]] + "\n")

    def _legacy_read(self, args: list[str]) -> bool:
        """`repos/<owner>/<name>` and its default branch's rules, which `_repo_read` serves."""
        repo = f"repos/{h.OWNER}/{h.REPO_NAME}"
        return args in (["api", repo], ["api", f"{repo}/rules/branches/{self.default_branch}"])

    def _rest(self, args: list[str], token: str | None) -> subprocess.CompletedProcess[str]:
        """The rulesets, check runs, collaborator and invitation endpoints."""
        repo = f"repos/{h.OWNER}/{h.REPO_NAME}"
        method, endpoint = "GET", next(arg for arg in args[1:] if not arg.startswith("-"))
        if "-X" in args:
            method, endpoint = args[args.index("-X") + 1 : args.index("-X") + 3]
        if (method, endpoint) == ("GET", f"{repo}/rulesets"):
            assert "--paginate" in args and "--slurp" in args, args
            keys = ("id", "name", "source_type")
            return h._done(args, [[{key: r[key] for key in keys} for r in self.rulesets.values()]])
        if method in {"POST", "PUT"} and endpoint.startswith(f"{repo}/rulesets"):
            body = json.loads(Path(args[args.index("--input") + 1]).read_text(encoding="utf-8"))
            ruleset_id = (
                int(endpoint.rsplit("/", 1)[1]) if method == "PUT" else 1000 + len(self.rulesets)
            )
            self.rulesets[ruleset_id] = {**body, "id": ruleset_id, "source_type": "Repository"}
            return h._done(args, self.rulesets[ruleset_id])
        if method == "GET" and endpoint.startswith(f"{repo}/rulesets/"):
            return h._done(args, self.rulesets[int(endpoint.rsplit("/", 1)[1])])
        prefix = f"{repo}/commits/{h.HEAD_SHA}/check-runs?check_name="
        if method == "GET" and endpoint.startswith(prefix):
            runs = [
                run
                for run in self.check_runs
                if run["name"] == unquote(endpoint.removeprefix(prefix))
            ]
            return h._done(args, {"total_count": len(runs), "check_runs": runs})
        return self._invitations(args, token, method, endpoint)

    def _invitations(
        self, args: list[str], token: str | None, method: str, endpoint: str
    ) -> subprocess.CompletedProcess[str]:
        """A collaborator `PUT` and the invitee's `user/repository_invitations`."""
        if method == "PUT" and endpoint.startswith(f"repos/{h.OWNER}/{h.REPO_NAME}/collaborators/"):
            assert args[-2:] == ["-f", "permission=push"], args
            invitation = {"id": 500 + len(self.invitations), "login": endpoint.rsplit("/", 1)[1]}
            self.invitations.append(invitation)
            return h._done(args, {"id": invitation["id"]})
        login = next((name for name, value in self.tokens.items() if value == token), None)
        if (method, endpoint) == ("GET", "user/repository_invitations"):
            full_name = {"full_name": f"{h.OWNER}/{h.REPO_NAME}"}
            mine = [
                {"id": i["id"], "repository": full_name}
                for i in self.invitations
                if i["login"] == login
            ]
            return h._done(args, mine)
        if method == "PATCH" and endpoint.startswith("user/repository_invitations/"):
            (accepted,) = [
                i for i in self.invitations if i["id"] == int(endpoint.rsplit("/", 1)[1])
            ]
            assert accepted["login"] == login, (args, login)
            self.invitations.remove(accepted)
            self.permissions[str(token)] = "WRITE"
            return h._done(args)
        raise AssertionError(f"unexpected gh api call: {args}")
