import test from "node:test";
import assert from "node:assert/strict";
import { checkpointSaveStatus } from "../src/lib/training-storage.ts";

const receipt = { schema_version: "checkpoint_receipt_v1", model_id: "model", checkpoint_slot: 7,
  sha256: "a".repeat(64), local_saved: true, cloud_uploaded: true };
const event = { type: "checkpoint_saved", model_id: "model", episode: 7, storage: receipt };

test("cloud success is shown only for the matching checkpoint receipt", () => {
  assert.equal(checkpointSaveStatus(event), "Checkpoint at episode 7 saved locally and uploaded to cloud.");
  assert.match(checkpointSaveStatus({ ...event, storage: { ...receipt, model_id: "other" } }), /not reported/);
  assert.match(checkpointSaveStatus({ ...event, storage: { ...receipt, checkpoint_slot: 8 } }), /not reported/);
});
test("local fallback is visible when upload fails", () => {
  assert.equal(checkpointSaveStatus({ ...event, storage: { ...receipt, cloud_uploaded: false } }),
    "Checkpoint at episode 7 saved locally. Cloud upload failed.");
});
test("selected alias upload failure remains distinct from numbered checkpoint success", () => {
  assert.match(checkpointSaveStatus({ ...event, selected_alias_storage: { ...receipt, checkpoint_slot: 0, cloud_uploaded: false } }),
    /Selected checkpoint alias remains local/);
});
test("legacy or malformed receipts never imply cloud success", () => {
  for (const storage of [null, {}, { ...receipt, sha256: "fake" }, { ...receipt, cloud_uploaded: "true" }]) {
    assert.doesNotMatch(checkpointSaveStatus({ ...event, storage }), /uploaded to cloud/);
  }
  assert.equal(checkpointSaveStatus(null), "Checkpoint storage status unavailable");
});
