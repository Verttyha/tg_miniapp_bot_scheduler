# Architecture Decisions

## 2026-04-03: Simplify the repository for direct server deployment

Decision:

- remove tunnel-specific scripts, helpers, and tests
- keep webhook behavior driven by `BASE_URL`
- treat the project as a normal server deployment behind a public HTTPS domain

Why:

- tunnel tooling was not part of product runtime
- the deployment model is simpler and easier to maintain without that layer

## 2026-04-03: Split backend into `core` and `domain`

Decision:

- keep runtime primitives in `scheduler_app/core`
- keep SQLAlchemy models and Pydantic schemas in `scheduler_app/domain`

Why:

- the old flat backend layout mixed unrelated concerns
- the new split is easier to navigate and maintain

## 2026-04-03: Keep the Mini App on a dark dashboard-style UI

Decision:

- keep routes and business flows intact
- use a dark dashboard home screen as the default entry point

Why:

- the UI is easier to scan on mobile and inside Telegram
- visual modernization was possible without changing server behavior

## 2026-04-03: Split the Mini App into route pages, shared components, hooks, helpers, and style layers

Decision:

- keep `src/app.tsx` as a thin route shell only
- move route-level logic into `src/pages`
- move shared UI into `src/components`
- keep session/bootstrap logic in `src/hooks`
- keep formatting/date/workspace helpers in `src/lib`
- replace the single `styles.css` file with layered CSS files imported from `src/styles/index.css`

Why:

- the previous frontend was too dense to evolve safely
- smaller files make future UI work faster and less error-prone
- decomposed CSS is easier to maintain without breaking unrelated screens
