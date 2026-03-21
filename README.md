# cicd-lists-build

CI/CD pipeline for managing XSOAR/XSIAM lists via Git.

## Project Structure

```
Packs/
  <PackName>/
    Lists/
      <ListName>/
        <ListName>.json         # demisto-sdk metadata (XSOAR/XSIAM format)
        <ListName>_data.<ext>   # Raw list data file
        metadata.yaml           # CI/CD validation config
scripts/
  validate.py                   # Main validation script
  upload.py                     # Deploy script using demisto-sdk
  custom_validators/            # Custom validation scripts
    default.py                  # Default custom validator
.github/workflows/
  validate-pr.yml               # PR validation + auto-merge
  deploy-lists.yml              # Deploy on merge to main
```

## metadata.yaml

Each list directory can optionally contain a `metadata.yaml` to configure CI/CD
validation. If omitted, the validator falls back to the `name` and `type` from
`<ListName>.json`.

| Field       | Required | Description |
|-------------|----------|-------------|
| `name`      | No       | Display name for validation output (falls back to `.json` name) |
| `type`      | No       | Validation type: `json`, `csv`, or `plain_text` (falls back to `.json` type) |
| `validator` | No       | Name of a custom validator in `scripts/custom_validators/` |

When `validator` is set, it overrides the type-based validation. This is useful
when the data format needs specific handling (e.g., pipe-delimited CSV).

```yaml
# Standard CSV validation
name: Blocked IPs
type: csv

# CSV with a custom pipe-delimiter validator
name: Firewall Rules
type: csv
validator: pipe_delimited
```

## Adding a New List

1. Create the list directory: `Packs/<PackName>/Lists/<ListName>/`
2. Add the demisto-sdk metadata file: `<ListName>.json`
3. Add the data file: `<ListName>_data.<ext>`
4. Optionally add `metadata.yaml` to override validation type or use a custom validator
5. Open a PR to `main`

## Custom Validators

Custom validators live in `scripts/custom_validators/` and are referenced by
name in `metadata.yaml` via the `validator` field.

Each validator receives the data file path as the first argument and must exit
with code 0 on success or non-zero on failure.

## CI/CD Workflows

### PR Validation (`validate-pr.yml`)
- Triggers on PRs to `main` that modify files under `Packs/`
- Detects which lists changed and validates only those
- Auto-merges the PR on successful validation

### Deploy (`deploy-lists.yml`)
- Triggers on pushes to `main` that modify files under `Packs/`
- Uploads changed lists using `demisto-sdk`
- Requires three repository secrets:
  - `DEMISTO_BASE_URL` - XSOAR/XSIAM server URL
  - `DEMISTO_API_KEY` - API key for authentication
  - `XSIAM_AUTH_ID` - Auth ID for XSIAM

## Local Validation

```bash
pip install -r requirements.txt
python scripts/validate.py                                              # Validate all lists
python scripts/validate.py Packs/ListManagement/Lists/Aisummary        # Validate specific list
```
