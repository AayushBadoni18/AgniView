# Testing

Local checks:

```text
.venv/bin/python -m pytest backend/tests -q
.venv/bin/python -m compileall -q backend/agniview backend/tests
cd frontend && npm test && npm run build && npm audit --omit=dev
```

Real PostGIS check after `docker compose up -d`:

```text
docker compose run --rm --volume "D:\AgniView:/workspace:ro" --env TEST_DATABASE_URL=postgresql://agniview:agniview@postgres:5432/agniview backend sh -c "pip install --quiet pytest==8.3.4 && cd /tmp && PYTHONPATH=/workspace/backend python -m pytest /workspace/backend/tests -q -p no:cacheprovider"
```

Current result: 45 backend tests pass with PostGIS, 2 frontend tests pass, production build passes, compileall passes, and npm audit reports zero vulnerabilities. Coverage includes migration replay, real spatial matching, lock/reuse/anomaly transitions, FIRMS, OSM, HLS selection and COG windows, caches, API boundaries/failures, AI grounding/isolation, alerts, metrics, and exports.

Headless Chrome verified desktop rendering and an active responsive breakpoint with no document overflow. Token-backed Mapbox and credentialed FIRMS/Earthdata remain the only unexecuted runtime paths.
