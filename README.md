# promptwars-substance-use-disorders

## Deployment-ready Flask app

This project is set up to be deployed from GitHub using a standard WSGI entrypoint.

### Run locally

```bash
pip install -r requirements.txt
python app.py
```

### Deploy from Git

This repository now includes:
- a production WSGI entrypoint in [wsgi.py](wsgi.py)
- a Procfile for platforms such as Render, Railway, or Heroku
- a runtime specification in [runtime.txt](runtime.txt)

Set the following environment variables in your deployment platform:
- `SECRET_KEY`
- `LLM_API_KEY` (optional)
- `LLM_PROVIDER` (optional, defaults to `mock` when empty)
- `STT_ENGINE` (optional, defaults to `google`)
