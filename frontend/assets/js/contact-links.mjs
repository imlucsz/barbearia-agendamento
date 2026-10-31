export function whatsappUrl(value) {
  const phone = String(value ?? "").trim();
  if (!/^\+?[\d ()-]+$/.test(phone)) return null;
  let digits = phone.replace(/\D/g, "");
  if (!phone.startsWith("+")) {
    if (/^[1-9]{2}(?:[2-5]\d{7}|9\d{8})$/.test(digits)) digits = `55${digits}`;
    else if (!/^55[1-9]{2}(?:[2-5]\d{7}|9\d{8})$/.test(digits)) return null;
  }
  return /^[1-9]\d{9,14}$/.test(digits) ? `https://wa.me/${digits}` : null;
}

export function mapsUrls(value, address) {
  let embed = null;
  let navigation = null;
  try {
    const url = new URL(value);
    const host = ["www.google.com", "google.com", "maps.google.com", "www.google.com.br", "google.com.br", "maps.google.com.br"].includes(url.hostname);
    if (url.protocol === "https:" && host && !url.username && !url.password && !url.port && /^\/maps(?:\/|$)/.test(url.pathname)) {
      if (/^\/maps\/embed(?:\/|$)/.test(url.pathname)) embed = url.href;
      else if (/^\/maps\/?$|^\/maps\/(?:place|search|dir)(?:\/|$)|^\/maps\/@/.test(url.pathname)
          && !["url", "redirect", "redirect_uri", "continue", "target"].some(key => url.searchParams.has(key))) navigation = url.href;
    }
  } catch { /* Missing or untrusted URLs are never used. */ }
  if (!navigation && typeof address === "string" && address.trim() && address.length <= 300
      && !/[<>\u0000-\u001f\u007f]/.test(address)) {
    const search = new URL("https://www.google.com/maps/search/");
    search.search = new URLSearchParams({ api: "1", query: address.trim() }).toString();
    navigation = search.href;
  }
  return { embed, navigation };
}
