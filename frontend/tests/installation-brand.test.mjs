import test from "node:test";
import assert from "node:assert/strict";
import {
  DEFAULT_BRAND_NAME,
  DEFAULT_BRAND_MARK,
  DEFAULT_BRAND_TAGLINE,
  DEFAULT_THEME_COLOR,
  normalizeBrandConfiguration,
  normalizeInstallationCopy,
  validateBrandLogoUrl,
} from "../assets/js/installation-brand.mjs";

const pageUrl = "https://barbearia.example/pages/index.html";

test("uses the current brand and no custom logo when unset", () => {
  assert.deepEqual(normalizeBrandConfiguration({}, pageUrl), {
    name: DEFAULT_BRAND_NAME,
    mark: DEFAULT_BRAND_MARK,
    tagline: DEFAULT_BRAND_TAGLINE,
    logoUrl: null,
    themeColor: DEFAULT_THEME_COLOR,
  });
});

test("accepts a configured name, safe relative raster logo and theme color", () => {
  assert.deepEqual(normalizeBrandConfiguration({
    name: "Barbearia Horizonte",
    mark: "BH.",
    tagline: "CORTE COM IDENTIDADE",
    logoUrl: "../assets/branding/horizonte.webp",
    themeColor: "#1677aa",
  }, pageUrl), {
    name: "Barbearia Horizonte",
    mark: "BH.",
    tagline: "CORTE COM IDENTIDADE",
    logoUrl: "https://barbearia.example/assets/branding/horizonte.webp",
    themeColor: "#1677aa",
  });
});

test("uses installation copy with safe text limits and core fallback values", () => {
  assert.equal(normalizeInstallationCopy({ homeHeroDescription: "Barbearia do Bairro" }).homeHeroDescription, "Barbearia do Bairro");
  assert.equal(normalizeInstallationCopy({ consentText: "x".repeat(1501) }).consentText.startsWith("Li e aceito"), true);
  assert.equal(normalizeInstallationCopy({ homeHeroEyebrow: "   " }).homeHeroEyebrow, "Seu próximo visual começa aqui");
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
