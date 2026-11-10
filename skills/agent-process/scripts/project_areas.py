"""The project-areas step of `init.py`; not a command. With `--area`, the linked Project's — or
the copy's — `Area` options and area views become the given names while its options are the
template's; `manual` prints the row for a Project the step leaves alone."""

from __future__ import annotations

import argparse
import json
from typing import Any, Sequence

import manual
from steps import InstallError, Step

Project = tuple[str, int, str | None]


class Names(argparse.Action):
    """`--area`, repeatable: a non-empty name without `"`, which a view filter quotes, once."""

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: str | Sequence[Any] | None,
        option_string: str | None = None,
    ) -> None:
        names = getattr(namespace, self.dest)
        if not isinstance(values, str) or not values or '"' in values:
            raise argparse.ArgumentError(
                self, f"expected a non-empty name without '\"': {values!r}"
            )
        if values in names:
            raise argparse.ArgumentError(self, f"given more than once: {values}")
        setattr(namespace, self.dest, [*names, values])


def steps(target: manual.Target, linked: list[dict[str, Any]], names: list[str]) -> list[Step]:
    """The step for `names` over `linked`, the Projects linked to the repository. A state
    `init` cannot read has no step: its `manual project-areas` row says why."""
    if not names or len(linked) > 1:
        return []
    project: Project | None = None
    try:
        if not linked:
            where, template = "the copy", manual.template_options(target)
        else:
            url = linked[0].get("url")
            project = (target.repo.split("/")[0], int(linked[0]["number"]), url)
            state = manual.areas(target, project)
            where, template = url or "the linked Project", state.template
            if state.state != "template":
                why = "has no Area field" if state.state == "none" else "has its own Area options"
                return [Step("project-areas", "unchanged", f"{where} {why}")]
    except manual.Unreadable:
        return []
    dropped = ", ".join(name for name in template if name not in names) or "none"
    detail = f"{where}: Area options and area views {', '.join(names)}; dropping {dropped}"
    return [Step("project-areas", "planned", detail, lambda: _replace(target, project, names))]


def _replace(target: manual.Target, project: Project | None, names: list[str]) -> bool:
    """The views first, found by name so that a retry completes a failed run, then the
    options, which end the `template` state; with no `project`, the copy linked by now."""
    try:
        now = manual.areas(target, project)
    except manual.Unreadable as exc:
        raise InstallError(f"project-areas: cannot read: {exc}") from None
    if now.state != "template":
        raise InstallError(f"project-areas: {now.url} no longer has the template's Area options")
    _replace_views(target, now, names)
    options: list[str] = []
    for name in names:
        if name in now.options:
            options.append(f"options[][id]={now.options[name]}")
        options += [f"options[][name]={name}", "options[][color]=GRAY", "options[][description]="]
    _write(
        target,
        "($field:ID!,$options:[ProjectV2SingleSelectFieldOptionInput!]!){updateProjectV2Field("
        "input:{fieldId:$field,singleSelectOptions:$options}){clientMutationId}}",
        f"field={now.field}",
        *options,
    )
    return True


def _replace_views(target: manual.Target, now: manual.Areas, names: list[str]) -> None:
    """Each name's view gets its filter: the view of that name, else a view named after a
    dropped template option, renamed to keep its fields, else a new one. The views named after
    a dropped template option that remain are deleted."""
    by_name = {view["name"]: view for view in now.views}
    spare = [
        view for view in now.views if view["name"] in now.template and view["name"] not in names
    ]
    for name in names:
        found = by_name.get(name)
        if found is None and spare:
            found = spare.pop(0)
        elif found is None:
            made = _write(
                target,
                "($project:ID!,$name:String!){createProjectV2View(input:"
                "{projectId:$project,name:$name,layout:BOARD_LAYOUT}){projectV2View{id}}}",
                f"project={now.project}",
                f"name={name}",
            )
            found = {"id": made["data"]["createProjectV2View"]["projectV2View"]["id"]}
        if (found.get("name"), found.get("filter")) != (name, _filter(name)):
            _write(
                target,
                "($view:ID!,$name:String!,$filter:String!){updateProjectV2View(input:"
                "{viewId:$view,name:$name,filter:$filter}){clientMutationId}}",
                f"view={found['id']}",
                f"name={name}",
                f"filter={_filter(name)}",
            )
    for view in spare:
        _write(
            target,
            "($view:ID!){deleteProjectV2View(input:{viewId:$view}){clientMutationId}}",
            f"view={view['id']}",
        )


def _filter(name: str) -> str:
    return f'-status:Done area:"{name}"'


def _write(target: manual.Target, mutation: str, *fields: str) -> Any:
    """One GraphQL mutation with its variables as `-f` fields; its error names the step."""
    args = [arg for part in fields for arg in ("-f", part)]
    try:
        done = target.gh_write("api", "graphql", "-f", f"query=mutation{mutation}", *args)
    except InstallError as exc:
        raise InstallError(f"project-areas: {exc}") from None
    if done.stdout is None:
        raise InstallError("project-areas: `gh api graphql` output not captured")
    try:
        return json.loads(done.stdout)
    except json.JSONDecodeError:
        raise InstallError("project-areas: `gh api graphql` printed no JSON") from None
