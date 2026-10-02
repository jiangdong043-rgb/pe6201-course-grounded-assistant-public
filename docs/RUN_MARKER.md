# Run and reproduce without private GitHub access

## A. Public-only saved-results view

Clone or download this public repository. In its root, use Python 3.11+ (tested on 3.12), create/activate a virtual environment, install `requirements.txt`, then run:

```powershell
python src/web_app.py --project . --port 8765
```

Visit http://127.0.0.1:8765/. Saved metrics/charts are available without an API key, private corpus or model request. Missing-key/data status is expected. Do not click Compare in this mode. Dependency installation needs internet. Stop with Ctrl+C. Use port 8766 if 8765 is occupied. This does not deploy an online service.

## B. Complete historical evidence and course answering

No teacher GitHub username or invitation is needed. Obtain the CODE and PRIVATE_DATA ZIP attachments from the LMS submission and extract both to one NEW parent folder. They merge into `End-of-Course Project`. Work in that folder, not over the public repository, and use Python 3.11+ (superseding the old 3.10 statement):

```powershell
cd "End-of-Course Project"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python src/repro_check.py --project . --require-derived-data
python src/verify_release.py --project .
python src/web_app.py --project . --port 8765
```

These checks do not call a paid model. Full source re-extraction instructions are in the package's `docs/RUN_MARKER.md`; use a separate output path and do not overwrite frozen evidence. Do not run these full-evidence checks against only the public tree: withheld question/output/hash files are required.

Live generation requires your own OPENROUTER_API_KEY in the process environment and an account with model access/credit. Never put keys into source files or the question box. Restart the server after setting the environment. Compare makes two paid API requests and RAG sends selected private excerpts externally; obtain permission first. First retrieval may download local model weights. New responses can differ from historical outputs.

## Limits

Local saved-page routes and evidence checks were validated; a clean-machine installation and new live API calls are not claimed. The chart regeneration script uses Windows Arial; prebuilt PNGs are supplied. No authentication or public hosting hardening is implemented. Keep the server local and restricted materials off public GitHub.
