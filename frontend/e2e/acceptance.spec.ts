import { test, expect, Page } from "@playwright/test";

/**
 * Smoke-tests the core loop a team uses every day:
 * sign in → create an issue → find it → comment → move it on the board.
 *
 * Credentials come from env so this can run against any disposable environment.
 * The demo seed account was removed from this instance, so supply real ones:
 *   E2E_EMAIL=... E2E_PASSWORD=... npm run e2e
 * (These tests create real issues — point them at a disposable environment.)
 */
const EMAIL = process.env.E2E_EMAIL || "admin@lira.local";
const PASSWORD = process.env.E2E_PASSWORD || "Admin123!";
const PROJECT_KEY = process.env.E2E_PROJECT || "DOC";

async function login(page: Page) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(EMAIL);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/dashboard/);
}

test.describe("core workflow", () => {
  test("signs in and lands on the dashboard", async ({ page }) => {
    await login(page);
    await expect(page.getByRole("heading", { name: /Good to see you/ })).toBeVisible();
  });

  test("rejects bad credentials with a readable error", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel("Email").fill(EMAIL);
    await page.getByLabel("Password").fill("definitely-wrong");
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page.getByText(/invalid email or password/i)).toBeVisible();
  });

  test("creates an issue, comments on it, and moves it on the board", async ({ page }) => {
    await login(page);

    const title = `E2E smoke ${Date.now()}`;

    // Create via the global button
    await page.getByRole("button", { name: /New issue/ }).click();
    const dialog = page.getByRole("dialog", { name: "Create issue" });
    await expect(dialog).toBeVisible();
    await dialog.getByLabel("Project").selectOption(PROJECT_KEY);
    await dialog.getByLabel("Title").fill(title);
    await dialog.getByRole("button", { name: "Create issue" }).click();

    // Lands on the new issue's page
    await expect(page).toHaveURL(/\/issues\/[A-Z]+-\d+/);
    await expect(page.getByRole("heading", { name: title })).toBeVisible();
    const issueKey = (page.url().match(/\/issues\/([A-Z]+-\d+)/) || [])[1];
    expect(issueKey).toBeTruthy();

    // Comment on it
    const comment = "Looks good from the E2E run.";
    await page.getByPlaceholder(/Add a comment/).fill(comment);
    await page.getByRole("button", { name: "Comment" }).click();
    await expect(page.getByText(comment)).toBeVisible();

    // It appears on the board and can be moved via the status control
    await page.goto(`/projects/${PROJECT_KEY}/board`);
    await expect(page.getByText(issueKey!).first()).toBeVisible();

    await page.goto(`/issues/${issueKey}`);
    await page.getByLabel("Status").click();
    await page.getByRole("button", { name: "In Progress" }).click();
    await expect(page.getByLabel("Status")).toContainText("In Progress");

    // Activity records the transition in human-readable form
    await expect(page.getByText(/changed status from .* to In Progress/)).toBeVisible();
  });

  test("finds the issue through global search", async ({ page }) => {
    await login(page);
    await page.goto(`/projects/${PROJECT_KEY}/issues`);
    await expect(page.getByPlaceholder("Search issues…")).toBeVisible();
    await page.getByPlaceholder("Search issues…").fill("OCR");
    await expect(page.getByText(/OCR/).first()).toBeVisible();
  });

  test("keyboard shortcut opens the help dialog", async ({ page }) => {
    await login(page);
    await page.keyboard.press("?");
    await expect(page.getByRole("dialog", { name: "Keyboard shortcuts" })).toBeVisible();
  });

  test("theme can be switched to dark and persists", async ({ page }) => {
    await login(page);
    await page.goto("/settings");
    await page.getByRole("button", { name: "Dark", exact: true }).click();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
    await page.reload();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
    // reset so later runs start from a known state
    await page.getByRole("button", { name: "Light", exact: true }).click();
  });
});
