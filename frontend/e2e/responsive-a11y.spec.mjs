import { expect, test } from "@playwright/test";

const client = { email: "cliente.e2e@example.com", password: "E2E-Test-Client-Only-2026!" };
const admin = { email: "admin.e2e@example.com", password: "E2E-Test-Admin-Only-2026!" };

async function checkPage(page, path) {
  await page.goto(path);
  await page.locator("body").waitFor();
  await page.evaluate(() => document.fonts.ready);
  const overflow = await page.evaluate(() => ({
    viewport: document.documentElement.clientWidth,
    document: document.documentElement.scrollWidth,
    elements: [...document.querySelectorAll("body *")].map((node) => ({
      selector: `${node.tagName.toLowerCase()}${node.id ? `#${node.id}` : ""}.${[...node.classList].join(".")}`,
      right: Math.round(node.getBoundingClientRect().right),
      width: Math.round(node.getBoundingClientRect().width),
    })).filter((item) => item.right > document.documentElement.clientWidth + 1).slice(0, 8),
  }));
  expect(overflow.document, `horizontal overflow on ${path}: ${JSON.stringify(overflow.elements)}`).toBeLessThanOrEqual(overflow.viewport + 1);
  const unlabeled = await page.locator('input:not([type="hidden"]), select, textarea, button').evaluateAll((nodes) =>
    nodes.filter((node) => {
      if (node.disabled || node.getAttribute("aria-hidden") === "true") return false;
      const label = node.getAttribute("aria-label") || node.getAttribute("aria-labelledby") || node.labels?.length || node.innerText?.trim();
      return !label;
    }).map((node) => `${node.tagName.toLowerCase()}${node.id ? `#${node.id}` : ""}`),
  );
  expect(unlabeled, `unlabeled controls on ${path}`).toEqual([]);
}

test("public, client and admin screens fit viewport and support labeled keyboard focus", async ({ page }) => {
  for (const path of ["/pages/index.html", "/pages/catalog.html", "/pages/login.html", "/pages/cadastro.html"]) {
    await checkPage(page, path);
  }

  await page.goto("/pages/login.html");
  await page.getByLabel("E-mail").fill(client.email);
  await page.getByLabel("Senha", { exact: true }).fill(client.password);
  await page.getByRole("button", { name: "Entrar na minha conta" }).click();
  await page.waitForURL(/client-dashboard\.html$/);
  for (const path of ["/pages/client-dashboard.html", "/pages/client-appointments.html", "/pages/client-account.html"]) {
    await checkPage(page, path);
  }

  await page.goto("/pages/login.html");
  await page.getByLabel("E-mail").fill(admin.email);
  await page.getByLabel("Senha", { exact: true }).fill(admin.password);
  await page.getByRole("button", { name: "Entrar na minha conta" }).click();
  await page.waitForURL(/admin\.html$/);
  await checkPage(page, "/pages/admin.html");

  await page.goto("/pages/login.html");
  for (let index = 0; index < 4; index += 1) {
    await page.keyboard.press("Tab");
    const focused = await page.evaluate(() => {
      const element = document.activeElement;
      if (!(element instanceof HTMLElement) || element === document.body) return false;
      const rect = element.getBoundingClientRect();
      const style = getComputedStyle(element);
      return rect.width > 0 && rect.height > 0 && style.visibility !== "hidden"
        && style.outlineStyle !== "none" && parseFloat(style.outlineWidth) > 0;
    });
    expect(focused, "keyboard focus should be visible").toBe(true);
  }
});
