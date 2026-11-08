# Security review

## Scope and conclusion

Static review of the production code at branch `fix/admin-agenda-navigation`,
HEAD `00f2e44`. The review covered authentication and sessions, browser and
Render configuration, authorization, bookings, schemas, frontend rendering,
related tests, dependencies, and deployment settings.

No exploitable vulnerability was confirmed in the reviewed paths. The review
identified the following defense-in-depth and session-management risks; they
are not findings of a demonstrated attack path.

## Findings

### Medium — Frontend Content Security Policy does not restrict scripts

`render.yaml:70-71` configures only `frame-ancestors 'none'` for the static
site. This does not restrict scripts, connections, styles, or external
resources. The frontend uses an import map to load Three.js from jsDelivr, and
`frontend/scripts/build-static.mjs:38-41` copies the debug page into the
static output. The API's separate CSP in `backend/app/main.py:101-104` does
not set policy for the static HTML.

No user-controlled input to executable script flow was found in the dynamic
rendering paths examined. The current policy nevertheless offers little
defense if such a flaw or a compromise of externally loaded code occurs.
Define and validate a CSP compatible with the actual frontend resources, and
decide whether the public build should include the debug page. Published
headers were not checked.

### Medium — Authentication rate limiting is IP-based and race-prone

`backend/app/core/rate_limit.py:19,44,52,82,90-94` applies the limit by IP and
route, recording attempts after the response. `backend/app/core/config.py:382-383`
sets the default to five failed attempts over fifteen minutes. There is no
independent per-account budget, and concurrent requests can evaluate the same
history before either records its attempt.

`render.yaml:47` configures `cf-connecting-ip`, which
`backend/app/core/request_context.py:30-37` accepts when configured. The
review did not verify whether the deployed edge removes or overwrites
client-supplied values, so an IP-spoofing bypass is not confirmed. Validate
the trusted-proxy chain and consider per-account limits and concurrency-safe
recording.

### Medium — Access token is readable by same-origin JavaScript

`frontend/assets/js/api.js:12,25` reads and writes the access token in
`localStorage`. A script executing on the same origin could read it. This is
an exposure if another script-injection flaw or same-origin script compromise
occurs, not proof that such an XSS path exists. No exploitable path from
user-controlled data to an executable sink was identified in the rendering
paths examined.

Consider keeping the access token in memory while retaining the refresh token
in its `HttpOnly` cookie, and maintain effective CSP as defense in depth.

### Low — Revoked refresh sessions do not revoke issued access tokens

Password reset and other session actions revoke refresh tokens in
`backend/app/routers/auth.py`, but access JWTs remain accepted until their
expiration in `backend/app/core/security.py:40-46`. The configured access
token lifetime is five to sixty minutes, fifteen minutes by default.

An already-issued access token therefore retains a residual validity window
after refresh-session revocation. This is not an independent authentication
bypass. Decide whether immediate access-token invalidation is required; if
so, introduce an appropriate revocation or session-version strategy.

## Controls observed

- JWT decoding is restricted to the configured algorithm and requires
  expiration; authorization uses the current user and role from the backend.
- Password hashing uses Argon2 with legacy bcrypt verification support.
- Refresh tokens are stored as SHA-256 digests, issued through an `HttpOnly`
  cookie, rotated, and checked for reuse. The JSON responses do not expose
  the refresh token; related tests exist.
- Password-reset responses are generic, reset tokens are single-use and
  expiring, and the token is placed in the link fragment.
- CORS uses configured origins with credentials; refresh and logout validate
  `Origin`. The frontend sends credentials for refresh.
- Administrative routes and financial export enforce role checks; booking
  access checks ownership. Related authorization and booking-integrity tests
  exist.
- Dynamic administrative values examined are escaped or written as text;
  CSV output neutralizes formula-leading characters.
- OpenAPI documentation is disabled in production. No upload, `eval`, shell
  execution, or user-controlled external request URL was identified in the
  paths examined.

## Hypotheses reviewed

| Topic | Result |
|---|---|
| Access token in `localStorage` | Still present; conditional exposure described above. |
| Static-site CSP | Still incomplete; the API's policy does not cover static HTML. |
| Render cookie/refresh behavior | Code configures credentialed requests and an `HttpOnly`, production-`Secure`, `SameSite=Lax` cookie scoped to `/auth`; actual cross-service browser behavior and published headers were not tested. |
| Authentication rate limiting | Five failures/15 minutes by IP and route; race and proxy trust require operational validation. |
| Refresh token in JSON | Not present in the current responses; related tests verify this. |

## Limitations

This was a static review. Production was not accessed; published headers,
Render proxy behavior, and browser cookie behavior were not validated.
Automated tests and dependency vulnerability scanners were not run; cited
tests were inspected, not executed. No fuzzing, dynamic testing, PostgreSQL
concurrency testing, or line-by-line review of third-party/generated code was
performed. Findings describe the reviewed code and configuration at the HEAD
listed above.
