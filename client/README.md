# FlowSync client

Next.js application using React, TypeScript, React Three Fiber, Zustand,
TanStack Query and Prisma. The `src/app/` tree contains page and API routes;
`src/components/`, `src/hooks/`, `src/store/` and `src/types/` hold shared UI,
connections, state and contracts.

Use Node.js 24 and npm from this directory:

```bash
npm ci
npm run dev
npm run lint
npm run typecheck
npm run build
```

`package-lock.json` is the dependency lockfile. `npm ci` generates the Prisma
client through `postinstall`; it does not apply a database schema. Environment
configuration and database setup are described in [the setup guide](../docs/setup.md).
Keep database credentials server-side and exclude `.env.local` from commits.

The browser uses `NEXT_PUBLIC_FASTAPI_HTTP_URL` and
`NEXT_PUBLIC_FASTAPI_WS_URL`; both default to the local backend. Public Next.js
environment values are embedded during the build. Database access in
`src/app/api/` uses the server-side Prisma client.

Interactive camera, city and research pages are application features. Audited
headless results and limitations are documented separately in
[research status](../research/RESEARCH_STATUS.md).
