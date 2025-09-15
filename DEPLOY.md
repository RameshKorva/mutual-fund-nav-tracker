# Deploying to Streamlit Community Cloud

1. Push your code to GitHub (mutual-fund-nav-tracker repo).
2. Go to [streamlit.io/cloud](https://streamlit.io/cloud) and sign in with GitHub.
3. Click "New app" and select your mutual-fund-nav-tracker repository.
4. Set `app.py` as the entry point.
5. Click "Deploy".

Your app will be publicly accessible on a Streamlit URL!

## Notes
- The app fetches NAV data live from AMFI India each time you open or reload.
- For charts, you can customize or add filters (e.g., select funds, date range).
- For persistent storage or scheduled fetching, consider adding scheduled jobs or caching.

If you need custom features (filters, email alerts, authentication), just ask!