import test from "node:test";
import assert from "node:assert/strict";

import { filterQuery, savingsLabel } from "./ui.mjs";


test("filter query omits empty values and preserves active filters", () => {
  assert.equal(filterQuery({ classification: "wildfire", severity: "", minConfidence: "0.9" }), "classification=wildfire&minConfidence=0.9");
});

test("compute savings explains classification reuse", () => {
  assert.equal(savingsLabel({ reusedClassifications: 1, totalDetectionsProcessed: 4 }), "1 of 4 classifications reused (25%)");
  assert.equal(savingsLabel({ reusedClassifications: 0, totalDetectionsProcessed: 0 }), "No detections processed yet");
});
