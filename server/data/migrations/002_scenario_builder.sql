-- ============================================================
-- FlowSync: Scenario Builder — Supabase SQL Migration
-- Run this in your Supabase project → SQL Editor
-- ============================================================

-- 1. Named, reproducible benchmark scenarios
CREATE TABLE IF NOT EXISTS public.scenarios (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name             TEXT NOT NULL,
    seed             INTEGER NOT NULL,
    spawn_lambda     FLOAT NOT NULL DEFAULT 0.5,
    duration_seconds INTEGER NOT NULL DEFAULT 60,
    created_at       TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Per-run results: one row per (scenario x model_episode) execution
CREATE TABLE IF NOT EXISTS public.scenario_runs (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scenario_id      UUID NOT NULL REFERENCES public.scenarios(id) ON DELETE CASCADE,
    model_id         TEXT NOT NULL,
    model_episode    INTEGER NOT NULL,
    controller       TEXT NOT NULL DEFAULT 'ai',
    scenario_hash    TEXT NOT NULL,
    avg_wait_time    FLOAT,
    total_passed     INTEGER,
    max_queue        INTEGER,
    override_rate    FLOAT,
    ran_at           TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for fast lookup by scenario + episode
CREATE INDEX IF NOT EXISTS idx_scenario_runs_scenario_id
    ON public.scenario_runs(scenario_id);

CREATE INDEX IF NOT EXISTS idx_scenario_runs_model_episode
    ON public.scenario_runs(scenario_id, model_episode);

-- Enable RLS (service key bypasses — safe for server-side writes)
ALTER TABLE public.scenarios     ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.scenario_runs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "service_full_access_scenarios"
    ON public.scenarios FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "service_full_access_scenario_runs"
    ON public.scenario_runs FOR ALL USING (true) WITH CHECK (true);
