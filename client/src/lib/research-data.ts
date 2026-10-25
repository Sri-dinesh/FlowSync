import type { ResearchController, ResearchTelemetryFrame } from "../types/research";

export function parseControllers(payload: unknown): ResearchController[] {
  if (!payload || typeof payload !== "object" || !("controllers" in payload) || !Array.isArray(payload.controllers)) {
    throw new Error("Invalid controller catalog");
  }
  return payload.controllers.map((item: unknown) => {
    if (!item || typeof item !== "object" || !("id" in item) || typeof item.id !== "string"
      || !("name" in item) || typeof item.name !== "string"
      || !("description" in item) || typeof item.description !== "string"
      || !("available_live" in item) || typeof item.available_live !== "boolean") {
      throw new Error("Invalid controller availability metadata");
    }
    return {
      id: item.id, name: item.name, description: item.description,
      available_live: item.available_live,
      unavailable_reason: "unavailable_reason" in item && typeof item.unavailable_reason === "string" ? item.unavailable_reason : null,
      is_proposed_method: "is_proposed_method" in item && item.is_proposed_method === true,
      capabilities: {},
    };
  });
}

export function recordedSnapshot(frame: ResearchTelemetryFrame | null) {
  if (!frame) return null;
  return {
    experiment_id: frame.experiment_id,
    scenario_id: frame.scenario_id,
    scenario_hash: frame.scenario_hash || null,
    seed: frame.seed,
    controller: frame.controller,
    checkpoint_hash: /^[a-f\d]{64}$/i.test(frame.model_hash) ? frame.model_hash : null,
    runtime: frame.runtime ?? null,
    step: frame.step,
    sim_time_s: frame.sim_time_s,
    scope: "Recorded application telemetry snapshot; not an audited headless benchmark or final evaluation.",
    metrics: {
      mean_delay_s: frame.metrics.mean_delay_s ?? frame.metrics.delay_mean_s ?? null,
      p95_delay_s: frame.metrics.p95_delay_s ?? frame.metrics.delay_p95_s ?? null,
      queue_area_veh_s: frame.metrics.queue_area_veh_s ?? null,
      throughput: frame.metrics.throughput ?? frame.metrics.throughput_total_veh ?? null,
      executed_violations: frame.safety.executed_violations ?? null,
    },
  };
}

export function csvCell(value: string | number | null) {
  // Quote delimiters and neutralize spreadsheet formulas in imported run labels.
  const text = value === null ? "" : String(value);
  const safe = typeof value === "string" && /^[=+\-@\t\r]/.test(text) ? "'" + text : text;
  return '"' + safe.replaceAll('"', '""') + '"';
}

export function snapshotCsv(frame: ResearchTelemetryFrame | null) {
  const data = recordedSnapshot(frame);
  if (!data) return null;
  const columns = { experiment_id: data.experiment_id, scenario: data.scenario_id, seed: data.seed,
    controller: data.controller, ...data.metrics };
  return Object.keys(columns).join(",") + "\n" + Object.values(columns).map(csvCell).join(",") + "\n";
}

export function latexEscape(value: string) {
  const escaped: Record<string, string> = {
    "\\": "\\textbackslash{}", "&": "\\&", "%": "\\%", "$": "\\$", "#": "\\#",
    "_": "\\_", "{": "\\{", "}": "\\}", "~": "\\textasciitilde{}", "^": "\\textasciicircum{}",
  };
  return value.replace(/[\\&%$#_{}~^]/g, (c) => escaped[c]);
}

export function snapshotLatex(frame: ResearchTelemetryFrame | null) {
  const data = recordedSnapshot(frame);
  if (!data) return null;
  const m = data.metrics;
  return ["% One application telemetry snapshot; not a comparative benchmark.",
    "\\begin{tabular}{lrrrr}",
    "Controller & Mean wait (s) & P95 wait (s) & Passed & Recorded violations \\\\",
    "\\hline",
    [latexEscape(data.controller), m.mean_delay_s ?? "--", m.p95_delay_s ?? "--", m.throughput ?? "--", m.executed_violations ?? "--"].join(" & ") + " \\\\",
    "\\end{tabular}"].join("\n");
}
