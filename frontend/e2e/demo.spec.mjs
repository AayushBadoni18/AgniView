import { expect, test } from "@playwright/test";

test("canonical demo flow keeps event AI context isolated", async ({ page }) => {
  const errors = [];
  page.on("console", (message) => { if (message.type() === "error") errors.push(message.text()); });
  page.on("pageerror", (error) => errors.push(error.message));

  await page.goto("/");
  await expect(page.getByRole("status")).toHaveText("4 events");
  await expect(page.getByText("1 of 4 classifications reused (25%)")).toBeVisible();

  await page.getByRole("button", { name: /wildfire.*126\.4 MW/i }).click();
  await expect(page.getByRole("heading", { name: "Wildfire" })).toBeVisible();
  await expect(page.getByText("Anomaly forced full re-evaluation")).toBeVisible();
  await expect(page.locator(".timeline")).toContainText("reused");

  await page.getByLabel("Ask AI about this point…").fill("What is the measured FRP?");
  await page.getByRole("button", { name: "Ask" }).click();
  await expect(page.locator(".answer")).toContainText("126.4 MW");

  await page.getByRole("button", { name: /industrial.*38\.2 MW/i }).click();
  await expect(page.getByRole("heading", { name: "Industrial", exact: true })).toBeVisible();
  await expect(page.locator(".answer")).toHaveCount(0);

  await page.getByLabel("Classification").selectOption("wildfire");
  await expect(page.getByRole("status")).toHaveText("2 events");
  await expect(page.locator(".map-fallback button")).toHaveCount(2);
  await expect(page.getByRole("link", { name: "CSV" })).toHaveAttribute("href", /classification=wildfire/);
  expect(errors).toEqual([]);
});
