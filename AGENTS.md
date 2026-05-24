# Agent Instructions — Smart Traffic Simulation

## Read First
Always read PLAN.md before starting any work. Work phase by phase.
Mark checkboxes complete after each task: `- [x]`.

## Package Manager
Always use `pnpm`. Never npm or yarn.

## Project Structure
- client/ → Next.js app (pnpm workspace)
- server/ → FastAPI Python app

## Code Rules
- TypeScript: strict mode, no `any`
- Python: type hints on every function
- Never hardcode env vars — always use .env files
- Prisma schema lives in client/prisma/schema.prisma
- All FastAPI Supabase writes use server/app/services/supabase_service.py

## Running Things
- Frontend: cd client && pnpm dev
- Backend: cd server && uvicorn app.main:app --reload
- Both: run in separate terminals

## Never Do
- Don't run `npm install` or `yarn`
- Don't create files outside client/ or server/ except config files
- Don't commit .env files
- Don't skip phases in PLAN.md