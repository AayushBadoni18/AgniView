# Testing

Local checks:

```text
.venv/bin/python -m pytest backend/tests -q
.venv/bin/python -m compileall -q backend/agniview backend/tests
cd frontend && npm test && npm run build && npm audit --omit=dev
```

Real PostGIS checks must use a dedicated disposable database named `agniview_test`
or `agniview_test_*`. The test rejects all other database names before connecting
and checks the actual connected database before destructive setup. Never use the
normal application database. CI already uses `agniview_test`.

Create the test database with your configured database administrator, then set
`TEST_DATABASE_URL` securely to its PostgreSQL URI (no query string or fragment).
Do not paste credentials into logs or command history. Run:

```text
python -m pytest backend/tests -q
```

Current result: 45 backend tests pass with PostGIS, 2 frontend tests pass, production build passes, compileall passes, and npm audit reports zero vulnerabilities. Coverage includes migration replay, real spatial matching, lock/reuse/anomaly transitions, FIRMS, OSM, HLS selection and COG windows, caches, API boundaries/failures, AI grounding/isolation, alerts, metrics, and exports.

Headless Chrome verified desktop rendering and an active responsive breakpoint with no document overflow. Token-backed Mapbox and credentialed FIRMS/Earthdata remain the only unexecuted runtime paths.
