import test from "node:test";
import assert from "node:assert/strict";
import {
  DEFAULT_BRAND_NAME,
  DEFAULT_THEME_COLOR,
  normalizeBrandConfiguration,
  validateBrandLogoUrl,
} from "../assets/js/installation-brand.mjs";

const pageUrl = "https://barbearia.example/pages/index.html";

test("uses the current brand and no custom logo when unset", () => {
  assert.deepEqual(normalizeBrandConfiguration({}, pageUrl), {
    name: DEFAULT_BRAND_NAME,
    logoUrl: null,
    themeColor: DEFAULT_THEME_COLOR,
  });
});

test("accepts a configured name, safe relative raster logo and theme color", () => {
  assert.deepEqual(normalizeBrandConfiguration({
    name: "Barbearia Horizonte",
    logoUrl: "../assets/branding/horizonte.webp",
    themeColor: "#1677aa",
  }, pageUrl), {
    name: "Barbearia Horizonte",
    logoUrl: "https://barbearia.example/assets/branding/horizonte.webp",
    themeColor: "#1677aa",
  });
});

test("accepts an HTTPS raster image URL for a separately hosted installation asset", () => {
  assert.equal(
    validateBrandLogoUrl("https://cdn.example.net/brands/horizonte.avif", pageUrl),
    "https://cdn.example.net/brands/horizonte.avif",
  );
});

test("rejects script schemes, traversal, non-raster formats and unsafe URL components", () => {
  for (const value of [
    "javascript:alert(1)",
    "data:image/png;base64,AAAA",
    "//cdn.example.net/brand.png",
    "http://cdn.example.net/brand.png",
    "../../outside/logo.png",
    "../assets/branding/../../outside.png",
    "../assets/branding/logo.svg",
    "https://cdn.example.net/brands/logo.png?token=private",
    "https://user:pass@cdn.example.net/brands/logo.png",
  ]) {
    assert.equal(validateBrandLogoUrl(value, pageUrl), null, value);
  }
});

test("falls back safely for invalid names and never rewrites markup as HTML", () => {
  const maliciousName = "<img src=x onerror=alert(1)>";
  const normalized = normalizeBrandConfiguration({ name: maliciousName, themeColor: "red" }, pageUrl);
  assert.equal(normalized.name, maliciousName);
  assert.equal(normalized.themeColor, DEFAULT_THEME_COLOR);
  assert.equal(normalizeBrandConfiguration({ name: "x".repeat(81) }, pageUrl).name, DEFAULT_BRAND_NAME);
  // The browser applier assigns this value through textContent, never innerHTML.
});
