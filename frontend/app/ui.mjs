export function filterQuery(filters) {
  return new URLSearchParams(Object.entries(filters).filter(([, value]) => value)).toString();
}

export function savingsLabel(metrics) {
  const total = metrics?.totalDetectionsProcessed || 0;
  if (!total) return "No detections processed yet";
  const reused = metrics.reusedClassifications || 0;
  return `${reused} of ${total} classifications reused (${Math.round(reused / total * 100)}%)`;
}
