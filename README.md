# NEXUS Trading Dashboard

The project is now a real web application built with:

- `Flask` backend
- `HTML / CSS / JavaScript` frontend
- TradingView widget
- strategy-aware analysis APIs
- news and economic-calendar APIs

## Run locally

```bash
pip install -r requirements.txt
python app.py
```

Then open:

```bash
http://127.0.0.1:5000
```

## Optional environment variables

- `GNEWS_API_KEY`
- `NEWSAPI_KEY`
- `TRADING_ECONOMICS_API_KEY`

## Deploy

You can deploy this app on:

- Render
- Railway
- Fly.io
- a VPS with Gunicorn + Nginx

### Quick Render deployment

1. Push the project to GitHub.
2. Create a new `Web Service` on Render.
3. Connect your GitHub repository.
4. Use:
   - `Build Command`: `pip install -r requirements.txt`
   - `Start Command`: `gunicorn app:app`
5. Add any optional environment variables you want:
   - `GNEWS_API_KEY`
   - `NEWSAPI_KEY`
   - `TRADING_ECONOMICS_API_KEY`
6. Deploy and wait for the public URL.

## Notes

- Streamlit is no longer used.
- The UI is now fully customizable as a normal website.
