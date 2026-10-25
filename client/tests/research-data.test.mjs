import test from "node:test";
import assert from "node:assert/strict";
import { parseControllers, recordedSnapshot, snapshotCsv, snapshotLatex } from "../src/lib/research-data.ts";

const frame = {
  experiment_id: "exp_real", scenario_id: "test_actual_01", scenario_hash: "real-scenario-hash",
  seed: 202, controller: "max_pressure", model_hash: "", step: 12, sim_time_s: 1.2,
  metrics: { mean_delay_s: 0, p95_delay_s: 2.5, queue_area_veh_s: 6, throughput: 3 },
  safety: { executed_violations: 2 },
};

test("no telemetry produces no export or invented metrics", () => {
  assert.equal(recordedSnapshot(null), null);
  assert.equal(snapshotCsv(null), null);
  assert.equal(snapshotLatex(null), null);
});
test("export uses the received frame identity, canonical fields and measured nonzero violations", () => {
  const data = recordedSnapshot(frame);
  assert.equal(data.scenario_id, "test_actual_01");
  assert.equal(data.seed, 202);
  assert.equal(data.checkpoint_hash, null);
  assert.equal(data.metrics.mean_delay_s, 0);
  assert.equal(data.metrics.executed_violations, 2);
  assert.match(snapshotLatex(frame), /max\\_pressure & 0 & 2.5 & 3 & 2/);
  assert.doesNotMatch(snapshotLatex(frame), /D3QN|Fixed-Time|58\.2/);
});
test("a received checkpoint hash is preserved without a default model label", () => {
  assert.equal(recordedSnapshot({ ...frame, model_hash: "a".repeat(64) }).checkpoint_hash, "a".repeat(64));
  assert.equal(recordedSnapshot({ ...frame, model_hash: "d3qn_canonical_v6_best" }).checkpoint_hash, null);
});
test("missing measurements stay null and spreadsheet labels are safely escaped", () => {
  const missing = { ...frame, metrics: {}, controller: '=HYPERLINK("bad")' };
  assert.equal(recordedSnapshot(missing).metrics.mean_delay_s, null);
  assert.match(snapshotCsv(missing), /'=HYPERLINK\(""bad""\)/);
  assert.match(snapshotLatex(missing), /-- & -- & --/);
});
test("controller availability must come from the backend contract", () => {
  const catalog = { controllers: [{ id: "d3qn", name: "D3QN", description: "Replay only", available_live: false, unavailable_reason: "No checkpoint adapter" }] };
  assert.equal(parseControllers(catalog)[0].available_live, false);
  assert.throws(() => parseControllers({ controllers: [{ id: "d3qn" }] }));
  assert.throws(() => parseControllers(null));
});
