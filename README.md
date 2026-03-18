# cicd-lists-build

CI/CD pipeline for managing XSOAR/XSIAM lists.

## Project Structure

```
Lists/
  <list-name>/
    metadata.yml     # List metadata (id, name, type, description)
    data.<ext>       # Raw list data file (json, csv, or txt)
scripts/
  validate.py        # Main validation script
  upload.py          # Deploy script using demisto-sdk
  custom_validators/ # Custom validation scripts per list
    default.py       # Default custom validator
.github/workflows/
  validate-pr.yml    # PR validation + auto-merge
  deploy-lists.yml   # Deploy on merge to main
```

## List Types

Each list directory contains a `metadata.yml` and a data file. The `type` field
in metadata determines which validator runs:

| Type     | Validator                                    |
|----------|----------------------------------------------|
| `json`   | Checks the data file is valid JSON           |
| `csv`    | Checks the data file is valid CSV with consistent columns |
| `custom` | Runs a Python script from `scripts/custom_validators/` |

## Adding a New List

1. Create a directory under `Lists/` (e.g., `Lists/my-ip-list/`)
2. Add `metadata.yml`:
   ```yaml
   id: my-ip-list
   name: My IP List
   type: json
   description: List of blocked IPs.
   ```
3. Add the data file (e.g., `data.json`)
4. Open a PR to `main`

## Custom Validators

For lists with `type: custom`, the validation script looks for
`scripts/custom_validators/<list-directory-name>.py`. If not found, it falls
back to `scripts/custom_validators/default.py`.

Custom validators receive the data file path as the first argument and must
exit with code 0 on success or non-zero on failure.

## CI/CD Workflows

### PR Validation (`validate-pr.yml`)
- Triggers on PRs to `main` that modify files under `Lists/`
- Detects which lists changed and validates only those
- Auto-merges the PR on successful validation

### Deploy (`deploy-lists.yml`)
- Triggers on pushes to `main` that modify files under `Lists/`
- Uploads changed lists using `demisto-sdk`
- Requires three repository secrets:
  - `DEMISTO_BASE_URL` - XSOAR/XSIAM server URL
  - `DEMISTO_API_KEY` - API key for authentication
  - `XSIAM_AUTH_ID` - Auth ID for XSIAM

## Local Validation

```bash
pip install -r requirements.txt
python scripts/validate.py                          # Validate all lists
python scripts/validate.py Lists/sample-json-list   # Validate specific list
```
