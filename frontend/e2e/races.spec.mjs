import { expect, test } from "@playwright/test";

const events = [
  { id: "a", classification: "industrial", latitude: 20, longitude: 78, frp: 10, confidence: .92, severity: "low", detectedAt: "2026-09-08T10:00:00Z" },
  { id: "b", classification: "wildfire", latitude: 21, longitude: 79, frp: 20, confidence: .90, severity: "high", detectedAt: "2026-09-08T11:00:00Z" },
];
const collection = data => ({ type: "FeatureCollection", features: data.map(properties => ({
  type: "Feature", geometry: { type: "Point", coordinates: [properties.longitude, properties.latitude] }, properties,
})) });
const deferred = () => { let resolve; const promise = new Promise(done => { resolve = done; }); return { promise, resolve }; };
const renderNextFrame = page => page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));

async function mockApi(page) {
  await page.route("**/api/**", async route => {
    const path = new URL(route.request().url()).pathname;
    const event = events.find(item => path.startsWith(`/api/events/${item.id}`));
    const json = path.endsWith("/map") ? collection(events) : path.endsWith("/metrics") ? {} :
      path.endsWith("/ai-summary") ? { event_id: event.id, summary: `Summary ${event.id}` } :
      path.endsWith("/history") ? { data: [] } : event;
    await route.fulfill({ json });
  });
}

test("slower event and AI responses cannot replace the active event", async ({ page }) => {
  await mockApi(page);
  const detail = deferred();
  const started = deferred();
  await page.route("**/api/events/a", async route => { started.resolve(); await detail.promise; await route.fulfill({ json: events[0] }); });
  await page.goto("/");
  await page.getByRole("button", { name: /industrial.*10 MW/i }).click();
  await started.promise;
  await page.getByRole("button", { name: /wildfire.*20 MW/i }).click();
  await expect(page.locator("aside")).toContainText("Summary b");
  detail.resolve();
  await renderNextFrame(page);
  await expect(page.locator("aside")).toContainText("Summary b");

  const answer = deferred();
  const asked = deferred();
  await page.route("**/api/events/b/ask", async route => { asked.resolve(); await answer.promise; await route.fulfill({ json: { event_id: "b", answer: "Only Event B answer" } }); });
  await page.getByLabel("Ask AI about this point…").fill("Why?");
  await page.getByRole("button", { name: "Ask", exact: true }).click();
  await asked.promise;
  await page.getByRole("button", { name: /industrial.*10 MW/i }).click();
  await expect(page.locator("aside")).toContainText("Summary a");
  answer.resolve();
  await renderNextFrame(page);
  await expect(page.locator("aside")).not.toContainText("Only Event B answer");
  await expect(page.locator(".answer")).toHaveCount(0);
});

test("filter responses cannot roll back newer filters; failures retry honestly", async ({ page }) => {
  await mockApi(page);
  const older = deferred();
  const requested = deferred();
  await page.route("**/api/events/map?**", async route => {
    const label = new URL(route.request().url()).searchParams.get("classification");
    if (label === "industrial") { requested.resolve(); await older.promise; }
    await route.fulfill({ json: collection(label ? events.filter(event => event.classification === label) : events) });
  });
  await page.goto("/");
  await expect(page.getByRole("status")).toHaveText("2 events");
  await page.getByRole("combobox", { name: "Classification", exact: true }).selectOption("industrial");
  await requested.promise;
  await page.getByRole("combobox", { name: "Classification", exact: true }).selectOption("wildfire");
  await expect(page.getByRole("button", { name: /wildfire.*20 MW/i })).toBeVisible();
  older.resolve();
  await renderNextFrame(page);
  await expect(page.getByRole("button", { name: /industrial.*10 MW/i })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "CSV", exact: true })).toHaveAttribute("href", /classification=wildfire/);
  await page.route("**/api/events/map?**", route => route.fulfill({ status: 503, json: {} }));
  await page.getByRole("combobox", { name: "Classification", exact: true }).selectOption("unknown");
  await expect(page.getByRole("alert").filter({ hasText: "Events unavailable" })).toBeVisible();
  await expect(page.getByText(/Loading mock/)).toHaveCount(0);
  await page.route("**/api/events/map?**", route => route.fulfill({ json: collection([]) }));
  await page.getByRole("button", { name: "Retry events" }).click();
  await expect(page.getByRole("status")).toContainText("0 events");
});

test("72-hour boundaries, reset and responsive evidence use real response data", async ({ page }) => {
  await page.clock.setFixedTime(new Date("2026-09-08T12:00:00Z"));
  await mockApi(page);
  await page.route("**/api/events/map?**", route => {
    const query = new URL(route.request().url()).searchParams;
    const start = query.get("start"), end = query.get("end");
    return route.fulfill({ json: collection(events.filter(event => (!start || event.detectedAt >= start) && (!end || event.detectedAt < end))) });
  });
  await page.goto("/");
  await expect(page.getByRole("status")).toHaveText("2 events");
  await page.getByRole("button", { name: "Explore previous 72 hours" }).click();
  const slider = page.getByRole("slider");
  await slider.press("Home");
  await expect(page.getByRole("status")).toHaveText("0 events");
  for (let hour = 0; hour < 36; hour++) await slider.press("ArrowRight");
  await expect(slider).toHaveValue("36");
  await expect(page.getByRole("status")).toHaveText("0 events");
  await slider.press("End");
  await expect(page.getByRole("status")).toHaveText("2 events");
  await expect(page.getByRole("link", { name: "CSV", exact: true })).toHaveAttribute("href", /start=.*end=/);
  await page.getByRole("button", { name: "Reset time filter" }).click();
  await expect(slider).toBeDisabled();
  await expect(page.getByRole("link", { name: "CSV", exact: true })).toHaveAttribute("href", "/api/exports/events.csv?");
  await page.getByRole("button", { name: /industrial.*10 MW/i }).click();
  await expect(page.locator("aside")).toContainText("Summary a");
  for (const width of [320, 768, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  }
});

