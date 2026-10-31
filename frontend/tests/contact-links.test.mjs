import test from "node:test";
import assert from "node:assert/strict";
import { whatsappUrl, mapsUrls } from "../assets/js/contact-links.mjs";

test("WhatsApp preserves explicit DDI and formats national Brazilian numbers", () => {
  for (const [input, digits] of [["+55 (11) 99999-0000","5511999990000"],["11999990000","5511999990000"],["(11) 99999-0000","5511999990000"],["+1 202-555-0123","12025550123"]]) {
    assert.equal(whatsappUrl(input), `https://wa.me/${digits}`);
  }
  for (const invalid of [null,undefined,"", "abc11999990000", "123", "+00000000000", "++12025550123", "12025550123", "11 1111-1111"]) assert.equal(whatsappUrl(invalid), null);
});

test("Maps separates embed from navigation and uses encoded institutional address", () => {
  const address = "Rua de Teste, 10 & esquina";
  const embed = mapsUrls("https://www.google.com/maps/embed?pb=test", address);
  assert.equal(embed.embed, "https://www.google.com/maps/embed?pb=test");
  assert.equal(new URL(embed.navigation).pathname, "/maps/search/");
  assert.equal(new URL(embed.navigation).searchParams.get("query"), address);
  assert.equal(mapsUrls("https://www.google.com/maps/place/Teste").navigation, "https://www.google.com/maps/place/Teste");
  for (const invalid of ["https://www.google.com/search?q=test", "https://www.google.com/url?q=https://evil.invalid", "https://google.com.evil.invalid/maps/", "javascript:alert(1)", "http://www.google.com/maps/", "https://user:password@www.google.com/maps/"]) {
    assert.deepEqual(mapsUrls(invalid), {embed:null,navigation:null});
  }
  assert.equal(new URL(mapsUrls(null,address).navigation).searchParams.get("query"), address);
  assert.deepEqual(mapsUrls(null,null), {embed:null,navigation:null});
  assert.deepEqual(mapsUrls("https://www.google.com/maps/preview/redirect?url=https://evil.invalid"), {embed:null,navigation:null});
  assert.deepEqual(mapsUrls("https://www.google.com/maps/?url=https://evil.invalid"), {embed:null,navigation:null});
  assert.equal(mapsUrls("https://www.google.com/maps/embed?pb=test").navigation, null);
  assert.deepEqual(mapsUrls("javascript:alert(1)", '<img src=x onerror="alert(1)">'), {embed:null,navigation:null});
});
