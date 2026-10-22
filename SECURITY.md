# Security

FlowSync is a research prototype intended for trusted development/simulation
environments. It is not a certified traffic-signal controller. The API includes
training, model, file/stream and database operations; this repository does not
provide a complete multi-user authentication/authorization boundary. Review
access control, CORS, network exposure, storage permissions and upload handling
before exposing an instance publicly.

## Credentials and data

- Keep `server/.env` and `client/.env.local` private.
- Never put Supabase secret/service-role keys or PostgreSQL passwords in
  `NEXT_PUBLIC_` variables, source files, notebooks, screenshots or issue reports.
- Use a dedicated development database and review reset/schema-management
  scripts before execution. Repository checks do not migrate a database.
- Treat external checkpoints and model files as untrusted inputs. Prefer known
  sources and validate hashes/metadata before loading them.
- Third-party detector datasets, footage and weights have separate licensing
  and privacy obligations; they are not bundled with the source license.

## Reporting

Use GitHub private vulnerability reporting if it is enabled for the repository.
Otherwise request a private contact channel from the maintainer without posting
sensitive details publicly. Do not include working credentials, private footage
or exploit data in a public issue. No response-time or support-period guarantee
is currently published.
