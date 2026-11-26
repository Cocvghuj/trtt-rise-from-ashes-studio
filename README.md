# RISE FROM ASHES — TRTT Voyage Studio

A mobile-first personal writing studio and controlled Blogger-draft workflow for TRTT Voyage.

## Files
- `index.html` — standalone responsive writing studio with live preview, Blogger HTML copy, and download.
- `blogger-drafts/rise-from-ashes.html` — reviewed Blogger post-body HTML for the personal reflection.
- `scripts/create_blogger_draft.py` — validates the article, checks for duplicates, creates a Blogger draft, and verifies readback.
- `.github/workflows/trtt-rise-from-ashes-blogger-draft.yml` — validates the PR and creates a Blogger draft after the article change is merged into `main`.
- `requirements-blogger.txt` — free Python client dependencies for the Blogger API.

## Publishing flow
1. Review the feature-branch pull request. The pull-request workflow validates the article without using credentials.
2. The Owner merges the pull request.
3. A push to `main` that includes the article path triggers the Blogger workflow.
4. The workflow uses this repository's GitHub Actions secrets to authenticate to the TRTT Voyage Blogger blog, checks for an existing matching post, creates a DRAFT only, then reads it back and verifies `status=DRAFT`.

Required repository secrets (names only; never commit values):
- `BLOGGER_BLOG_ID` — the TRTT Voyage blog ID, not the FlightScoutPro blog ID.
- `BLOGGER_CLIENT_ID`
- `BLOGGER_CLIENT_SECRET`
- `BLOGGER_REFRESH_TOKEN`

GitHub Actions secrets are repository-scoped. Credentials configured in a different repository are not automatically available here. If any required secret is missing or invalid, the workflow fails closed and reports the missing name or API error; it does not publish anything. Secret values are never printed.

## Safety
- The workflow creates Blogger DRAFTS only. It never calls a publish operation.
- Existing posts are never updated or deleted. A matching draft is verified and reused; a live-title collision or ambiguous match stops the workflow.
- No Telegram message is sent by this workflow. Telegram is reserved for a separately verified live Blogger post.
- No paid API, subscription, trial, or external runtime service is required.
- The browser writing studio itself does not connect to Blogger or publish content.

## Run locally
Open `index.html` in a modern browser. To validate the article without credentials:
```bash
python scripts/create_blogger_draft.py --validate-only
```

## Brand
TRTT Voyage — From Vision to Global Brand! Explore Beyond. Discover Everything.
ONE TEAM. ONE VISION. ONE JOURNEY.

Palette: Pink `#E98BAF`, Piyaji `#B77991`, Kathali `#D6A542`, Royal Midnight `#11152D`, White `#FFFFFF`.
