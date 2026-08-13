# AI Search Prototype — Demo Day Quick Start

Assumes the `pgv` Docker container and Python dependencies are already set
up on this machine. For a from-scratch setup, see the full **Setup** section
in `README.md`.

## Start it

```bash
docker start pgv
export DATABASE_URL=postgresql://postgres@localhost/search_proto
python -m uvicorn search:app --port 8000
```

If `uvicorn` isn't found: use `python -m uvicorn` (not the bare `uvicorn`
command) — that's what's verified working in this dev environment. If
`python` itself isn't found, try `py -m uvicorn` (Windows).

## Open it

**http://localhost:8000/**

This is a **local-only URL** — there is no public/hosted deployment. The
demo has to run from this machine, or be screen-shared. Nothing here is
reachable from another computer or the internet.

## Try it

- `shipyard with dock access`
- `bulk grain export terminal`
- `refrigerated warehouse`

Add a region (e.g. `Whyalla`, `Port Adelaide`) or resource (e.g.
`Warehousing`) to narrow results. Results show real photos, a green /
amber / red match-quality bar, and a "Best Match" badge on the top 3.

## Stop it

`Ctrl+C` the `uvicorn` process. The `pgv` container can keep running, or
stop it with `docker stop pgv`.
