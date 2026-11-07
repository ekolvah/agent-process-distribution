## Why

The baseline `detect-secrets` hook that `init` seeds into a created `.pre-commit-config.yaml`
runs without UTF-8 mode. On Windows, the platform encoding is `cp1252`, and the hook can
silently skip a whole file that contains a secret.

**Reproduction** (Windows 11, pre-commit 4.6.0, `PYTHONUTF8=0`, files tracked in a fresh git
repository, `pre-commit run -c <config> --hook-stage manual --all-files`):

- `ru.md`: `# Заметка про кириллицу` on line 1 and an `aws_secret_access_key` assignment of the AWS documentation example key on line 2
- `ru2.md`: `ключ сервиса: ` followed by the same assignment on line 1

| Config | `ru.md:2` | `ru2.md:1` |
|---|---|---|
| template hook (`Yelp/detect-secrets` `v1.5.0`, id `detect-secrets`) | reported | **not reported** |
| `repo: local`, `entry: python -X utf8 -m detect_secrets.pre_commit_hook`, `language: python`, `additional_dependencies: [detect-secrets==1.5.0]` | reported | reported |

Both runs exit 1, so the gate fails on `ru.md` alone and the miss stays hidden. With
`PYTHONUTF8=1` set globally, the template hook reports both files, which hides the bug.

**Root cause**: `detect_secrets/core/scan.py` 1.5.0, lines 261–270, opens the file with
`open(filename)`, which uses the locale encoding. On `UnicodeDecodeError` it runs `return`
under the comment `# We flat out ignore binary files`, so the hook skips the **whole file**
and logs nothing. Under `cp1252`, most UTF-8 Cyrillic decodes into mojibake without an error,
so `ru.md` is scanned. The UTF-8 encoding of `с` is `D1 81`, and `0x81` is undefined in
`cp1252`, so decoding `ru2.md` fails and the file is skipped.

## What Changes

- The template replaces the `Yelp/detect-secrets` remote hook with a local hook that runs
  the scanner in UTF-8 mode, pinned through `additional_dependencies` (design D1, D2).
- Configs that already exist are not touched, because `init` owns only the marker block.

## Capabilities

### New Capabilities

### Modified Capabilities
- `distribution`: *Init seeds the baseline toolchain*, with the seeded hook reworded and a
  new scenario added.

## Impact

- Edited: `skills/agent-process/templates/pre-commit-config.yaml`,
  `tests/publisher/test_init_config.py`,
  `.agent-process/docs/adr/0035-init-seeds-a-baseline-quality-toolchain.md`.
- No file is added or removed, and no dependency changes.
