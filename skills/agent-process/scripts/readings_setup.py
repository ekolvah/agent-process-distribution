"""The task-readings steps of `init.py` (change task-readings-auto-setup); not a command. From
the machine's `grafana` MCP server config they set the repository's `GRAFANA_URL` variable and
token secret and import the per-task dashboard; `manual` prints the row for what they cannot."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

import dashboard
import manual
from steps import InstallError, Step


class Client:
    """`manual.Grafana` over the stack's HTTP API with the token as a Bearer credential."""

    def __init__(self, url: str, token: str) -> None:
        self.url = url.rstrip("/")
        self.token = token

    def _call(self, method: str, path: str, body: Any = None) -> Any:
        request = urllib.request.Request(
            self.url + path,
            method=method,
            data=None if body is None else json.dumps(body).encode(),
            headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as exc:
            lines = exc.read().decode("utf-8", "replace").strip().splitlines()
            first = lines[0] if lines else exc.reason
            raise manual.Unreadable(f"{method} {path}: HTTP {exc.code}: {first}") from None
        except (OSError, ValueError) as exc:
            raise manual.Unreadable(f"{method} {path}: {exc}") from None

    def _list(self, path: str) -> list[dict[str, Any]]:
        data = self._call("GET", path)
        if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
            raise manual.Unreadable(f"GET {path} returned an unexpected shape")
        return data

    def datasources(self) -> list[dict[str, Any]]:
        return self._list("/api/datasources")

    def dashboard_titles(self, query: str) -> list[str]:
        path = "/api/search?" + urllib.parse.urlencode({"type": "dash-db", "query": query})
        return [str(item.get("title")) for item in self._list(path)]

    def post_dashboard(self, model: dict[str, Any]) -> str:
        done = self._call("POST", "/api/dashboards/db", {"dashboard": model, "overwrite": False})
        if not isinstance(done, dict) or not isinstance(done.get("url"), str):
            raise manual.Unreadable(f"POST /api/dashboards/db returned {done}")
        return self.url + done["url"]


def gh_step(
    t: manual.Target,
    label: str,
    done: bool,
    detail: str,
    *args: str,
    input: str | None = None,
) -> Step:
    """`unchanged`, or `planned` to run the `gh` write `args` (`input` on its standard input)."""

    def write() -> bool:
        try:
            t.gh_write(*args, input=input)
        except InstallError as exc:
            raise InstallError(f"{label}: {exc}") from None
        return True

    return Step(label, "unchanged" if done else "planned", detail, write)


def steps(t: manual.Target, secrets: dict[str, str] | manual.Unreadable) -> list[Step]:
    """The three steps while the config names a stack the repository does not contradict;
    `secrets` are the repository's secret names as `manual._kept` read them."""
    r = manual.readings(t, secrets)
    if r.url is None or r.token is None:
        return []
    found = [
        gh_step(
            t,
            "task-readings-url",
            r.variable == r.url,
            f"{manual.GRAFANA_URL} = {r.url}",
            "variable",
            "set",
            manual.GRAFANA_URL,
            "--body",
            r.url,
            "--repo",
            t.repo,
        ),
        gh_step(
            t,
            "task-readings-token",
            r.secret,
            f"{manual.GRAFANA_TOKEN} from {r.source}",
            "secret",
            "set",
            manual.GRAFANA_TOKEN,
            "--repo",
            t.repo,
            input=r.token,
        ),
    ]
    if r.dashboard or r.datasource is not None:
        found.append(_dashboard_step(t, r.title, r.url, r.datasource, r.token))
    return found


def _dashboard_step(
    t: manual.Target, title: str, url: str, datasource: str | None, token: str
) -> Step:
    label, detail = "task-readings-dashboard", f"{title} in {url}"
    if datasource is None:
        return Step(label, "unchanged", detail)

    def post() -> bool:
        text = json.dumps(dashboard.render([t.repo])).replace("${DS_INFINITY}", datasource)
        try:
            step.detail += f" at {t.grafana(url, token).post_dashboard(json.loads(text))}"
        except manual.Unreadable as exc:
            raise InstallError(f"{label}: {exc}") from None
        return True

    step = Step(label, "planned", f"{detail} with {datasource}", post)
    return step


if __name__ == "__main__":
    sys.exit("readings_setup.py is imported by init.py; run `agent-process init`")
