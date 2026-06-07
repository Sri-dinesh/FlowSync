FROM node:22-slim AS base
ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
RUN corepack enable
RUN apt-get update && apt-get install -y openssl && rm -rf /var/lib/apt/lists/*

FROM base AS deps
WORKDIR /app
COPY package.json pnpm-lock.yaml* ./
COPY prisma ./prisma/
RUN --mount=type=cache,id=pnpm,target=/pnpm/store \
    NODE_OPTIONS="--max-old-space-size=2048" pnpm install --ignore-scripts

FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Build-time environment variables
ARG NEXT_PUBLIC_FASTAPI_HTTP_URL
ARG NEXT_PUBLIC_FASTAPI_WS_URL
ENV NEXT_PUBLIC_FASTAPI_HTTP_URL=$NEXT_PUBLIC_FASTAPI_HTTP_URL
ENV NEXT_PUBLIC_FASTAPI_WS_URL=$NEXT_PUBLIC_FASTAPI_WS_URL

RUN npx prisma@6.19.3 generate
# Use standalone output for the smallest production image
RUN NODE_OPTIONS="--max-old-space-size=2048" pnpm build

FROM base AS runner
WORKDIR /app

ENV NODE_ENV=production

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]
