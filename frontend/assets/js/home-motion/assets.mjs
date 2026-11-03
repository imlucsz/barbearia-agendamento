// Original procedural artwork. Every instance has independent paint servers/pivots.
export function scissors(id) {
  return `<svg class="scissors" viewBox="70 115 560 380" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <defs>
    <linearGradient id="${id}-steel" x1="0" y1="0" x2=".22" y2="1"><stop stop-color="#191b1b"/><stop offset=".18" stop-color="#a6a7a1"/><stop offset=".32" stop-color="#f4f0dd"/><stop offset=".4" stop-color="#797e79"/><stop offset=".51" stop-color="#242b2a"/><stop offset=".67" stop-color="#c4c6b7"/><stop offset=".8" stop-color="#f7f4e5"/><stop offset="1" stop-color="#353c3c"/></linearGradient>
    <linearGradient id="${id}-edge"><stop stop-color="#73756d"/><stop offset=".35" stop-color="#fffce9"/><stop offset=".6" stop-color="#656b65"/><stop offset="1" stop-color="#dbdfd0"/></linearGradient>
    <linearGradient id="${id}-brass" x2=".8" y2="1"><stop stop-color="#29221a"/><stop offset=".3" stop-color="#b78d4c"/><stop offset=".48" stop-color="#ffe0a0"/><stop offset=".55" stop-color="#856338"/><stop offset=".8" stop-color="#d3b477"/><stop offset="1" stop-color="#463323"/></linearGradient>
    <linearGradient id="${id}-glint"><stop stop-color="#fffde7" stop-opacity="0"/><stop offset=".5" stop-color="#fffde7" stop-opacity=".9"/><stop offset="1" stop-color="#fffde7" stop-opacity="0"/></linearGradient>
    <clipPath id="${id}-blade"><path d="M286 293 Q357 283 477 285 L579 293 Q525 313 313 312Z"/></clipPath>
    <g id="${id}-half">
      <path d="M287 291 C262 291 243 314 219 342 L204 363 L223 379 C247 360 253 337 278 326 L312 311Z" fill="url(#${id}-steel)" stroke="#c0c2b5" stroke-width="1"/>
      <ellipse cx="179" cy="384" rx="57" ry="40" transform="rotate(-30 179 384)" fill="none" stroke="#101514" stroke-width="24"/>
      <ellipse cx="179" cy="381" rx="57" ry="40" transform="rotate(-30 179 381)" fill="none" stroke="url(#${id}-steel)" stroke-width="18"/>
      <ellipse cx="179" cy="381" rx="48" ry="31" transform="rotate(-30 179 381)" fill="none" stroke="#f3e8ca" stroke-opacity=".55" stroke-width="1.2"/>
      <path d="M286 293 Q357 283 477 285 L579 293 Q525 313 313 312Z" fill="url(#${id}-steel)" stroke="#b4b9ac" stroke-width="1.2"/>
      <path d="M318 309 Q474 310 573 294" fill="none" stroke="url(#${id}-edge)" stroke-width="3"/>
      <path d="M333 296 L519 292" stroke="#fffce9" stroke-opacity=".55" stroke-width="1"/>
      <g clip-path="url(#${id}-blade)"><rect class="blade-glint" x="250" y="267" width="70" height="75" fill="url(#${id}-glint)" transform="skewX(-25)"/></g>
      <path d="M151 418 Q122 434 109 413" fill="none" stroke="url(#${id}-steel)" stroke-width="10" stroke-linecap="round"/>
    </g>
  </defs>
  <g class="scissor-half half-back"><g transform="translate(0 600) scale(1 -1)"><use href="#${id}-half"/></g></g>
  <g class="scissor-half half-front"><use href="#${id}-half"/></g>
  <circle cx="300" cy="301" r="19" fill="#101514"/><circle cx="300" cy="298" r="16" fill="url(#${id}-brass)" stroke="#e9ce94" stroke-width="1"/><circle cx="300" cy="298" r="10" fill="url(#${id}-steel)"/><path d="M294 301 L306 295" stroke="#242b28" stroke-width="2.8" stroke-linecap="round"/>
  <path d="M328 303 H345" stroke="#343d35" stroke-width=".7"/><text x="349" y="303" font-family="monospace" font-size="4" fill="#28312d" letter-spacing="1">PRECISION</text>
  </svg>`;
}

export function pole(id) {
  return `<svg class="pole-svg" viewBox="0 0 240 620" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><defs>
  <linearGradient id="${id}-metal"><stop stop-color="#1c2020"/><stop offset=".12" stop-color="#797a6c"/><stop offset=".22" stop-color="#f3e4bc"/><stop offset=".29" stop-color="#8c744a"/><stop offset=".45" stop-color="#242a29"/><stop offset=".66" stop-color="#a5a28a"/><stop offset=".78" stop-color="#fff1c9"/><stop offset=".87" stop-color="#7a6c4d"/><stop offset="1" stop-color="#1c211f"/></linearGradient>
  <linearGradient id="${id}-glass"><stop stop-color="#000" stop-opacity=".85"/><stop offset=".25" stop-color="#000" stop-opacity="0"/><stop offset=".37" stop-color="#fff4ce" stop-opacity=".12"/><stop offset=".46" stop-color="#fff" stop-opacity=".75"/><stop offset=".49" stop-color="#fff" stop-opacity=".04"/><stop offset=".69" stop-color="#000" stop-opacity=".2"/><stop offset="1" stop-color="#000" stop-opacity=".86"/></linearGradient>
  <linearGradient id="${id}-ivory" x2="0" y2="1"><stop stop-color="#ddd4bb"/><stop offset="1" stop-color="#999380"/></linearGradient>
  <radialGradient id="${id}-cap" cx=".35" cy=".22" r=".8"><stop stop-color="#faf1cd"/><stop offset=".22" stop-color="#aca78a"/><stop offset=".48" stop-color="#46483e"/><stop offset=".75" stop-color="#1a1d1b"/><stop offset="1" stop-color="#a18a58"/></radialGradient>
  <pattern id="${id}-stripes" class="stripe-pattern" width="125" height="125" patternUnits="userSpaceOnUse" patternTransform="rotate(-32)"><rect width="125" height="125" fill="url(#${id}-ivory)"/><rect width="42" height="125" fill="#a9864e"/><rect x="43" width="38" height="125" fill="#202b29"/><rect x="43" width="2" height="125" fill="#e2c58a"/></pattern>
  <clipPath id="${id}-body"><rect x="70" y="116" width="100" height="390" rx="13"/></clipPath>
  </defs>
  <path d="M107 73 V40 Q120 26 133 40 V73" fill="url(#${id}-metal)"/>
  <ellipse cx="120" cy="100" rx="66" ry="43" fill="url(#${id}-cap)"/><rect x="54" y="99" width="132" height="25" rx="9" fill="url(#${id}-metal)"/>
  <rect x="64" y="123" width="112" height="378" rx="11" fill="#080d0c"/>
  <g clip-path="url(#${id}-body)"><rect x="70" y="116" width="100" height="390" fill="url(#${id}-stripes)"/><rect x="70" y="116" width="100" height="390" fill="url(#${id}-glass)"/></g>
  <path d="M76 132 V488 M165 132 V488" stroke="#c3d4c0" stroke-opacity=".4"/><path d="M96 138 V482" stroke="#ffffe0" stroke-width="2" stroke-opacity=".45"/>
  <rect x="54" y="498" width="132" height="25" rx="9" fill="url(#${id}-metal)"/><ellipse cx="120" cy="527" rx="66" ry="29" fill="url(#${id}-cap)"/>
  <path d="M74 105 H164 M74 516 H164" stroke="#faf1ce" stroke-opacity=".65"/><path d="M110 554 V581 Q120 594 130 581 V554" fill="url(#${id}-metal)"/>
  </svg>`;
}

export function mirror(id) {
  const shape='M110 820V300C110 145 225 54 400 54S690 145 690 300V820Z';
  const glass='M139 792V302C139 162 246 83 400 83S661 162 661 302V792Z';
  return `<svg class="mirror-svg" viewBox="0 0 800 900" xmlns="http://www.w3.org/2000/svg"><defs>
  <linearGradient id="${id}-frame" x1="0" y1=".1" x2="1" y2=".9"><stop stop-color="#22251f"/><stop offset=".13" stop-color="#a99363"/><stop offset=".21" stop-color="#fff0bc"/><stop offset=".27" stop-color="#554e38"/><stop offset=".48" stop-color="#202722"/><stop offset=".62" stop-color="#e0c58b"/><stop offset=".7" stop-color="#6d694c"/><stop offset=".91" stop-color="#c5ac70"/><stop offset="1" stop-color="#252c25"/></linearGradient>
  <linearGradient id="${id}-glass" x1="0" y1="0" x2=".9" y2="1"><stop stop-color="#4c5e55"/><stop offset=".27" stop-color="#172c28"/><stop offset=".52" stop-color="#324840"/><stop offset=".74" stop-color="#0b1917"/><stop offset="1" stop-color="#697165"/></linearGradient>
  <linearGradient id="${id}-figure" x2=".7" y2="1"><stop stop-color="#101c1a"/><stop offset=".5" stop-color="#1a2a26"/><stop offset="1" stop-color="#020b0a"/></linearGradient>
  <linearGradient id="${id}-fog" x2=".3" y2="1"><stop stop-color="#080f0d"/><stop offset=".65" stop-color="#18251f" stop-opacity=".97"/><stop offset="1" stop-color="#9ca387" stop-opacity=".05"/></linearGradient>
  <linearGradient id="${id}-sweep"><stop stop-color="#e9f4d6" stop-opacity="0"/><stop offset=".45" stop-color="#dff4db" stop-opacity=".02"/><stop offset=".52" stop-color="#f9f5da" stop-opacity=".32"/><stop offset=".59" stop-color="#e9f4d6" stop-opacity=".01"/><stop offset="1" stop-color="#e9f4d6" stop-opacity="0"/></linearGradient>
  <clipPath id="${id}-clip"><path d="${glass}"/></clipPath>
  </defs>
  <path d="M92 832V300C92 132 217 37 400 37S708 132 708 300V832Z" fill="#040b09"/>
  <path d="${shape}" fill="url(#${id}-frame)" stroke="#8a8566" stroke-width="1"/>
  <path class="frame-glow" d="M119 813V300C119 151 232 63 400 63S681 151 681 300V813Z" fill="none" stroke="#f3dca0" stroke-opacity=".7" stroke-width="2"/>
  <path d="${glass}" fill="url(#${id}-glass)" stroke="#a1a98b" stroke-opacity=".5" stroke-width="1.5"/>
  <g clip-path="url(#${id}-clip)">
    <g class="mirror-depth" stroke="#d4debd" stroke-opacity=".1" fill="none"><path d="M180 0V900 M620 0V900 M150 620H660 M185 0L300 900 M615 0L500 900"/><ellipse cx="400" cy="440" rx="360" ry="470"/></g>
    <ellipse class="mirror-aura" cx="400" cy="392" rx="217" ry="289" fill="#e6e2ab" opacity=".04"/>
    <g class="silhouette"><path d="M320 546C318 598 278 602 226 631L169 814H631L574 631C522 602 482 598 480 546L440 532H360Z" fill="url(#${id}-figure)"/><path d="M400 267C326 267 285 323 299 414L313 486C322 543 359 570 400 570S478 543 487 486L501 414C515 323 474 267 400 267Z" fill="url(#${id}-figure)" stroke="#9da991" stroke-opacity=".18"/><path class="finished-hair" d="M300 409C266 326 322 247 397 250C476 237 536 314 500 409L481 348C437 364 360 307 318 363Z" fill="#06100e"/><path d="M361 445Q400 455 439 445 M374 501Q400 511 426 501" fill="none" stroke="#b1baa0" stroke-opacity=".13"/></g>
    <g class="rough-lines" stroke="#7e8b74" stroke-opacity=".6" stroke-width="2" fill="none"><path d="M282 415C241 330 300 228 394 231C503 205 559 320 517 421"/><path d="M278 429C266 268 347 218 421 241C523 227 536 339 528 410"/><path d="M306 470L285 415 M493 476L519 414"/></g>
    <g class="precision-guides" fill="none" stroke="#dfc489" stroke-width="1"><path class="precision-line" d="M194 350H608"/><path class="precision-line" d="M194 407H608"/><path class="precision-line" d="M194 486H608"/><path class="precision-line" d="M400 188V670"/><path class="precision-line" d="M276 270V590"/><path class="precision-line" d="M523 270V590"/><circle cx="400" cy="405" r="178" stroke-dasharray="2 10"/><path d="M184 339V361 M616 339V361 M184 397V418 M616 397V418 M390 180H410 M390 678H410"/></g>
    <path class="result-contour" d="M303 409C279 328 326 258 397 260C478 247 525 320 497 409L481 348C437 364 360 307 318 363 M313 486C322 543 359 570 400 570S478 543 487 486" fill="none" stroke="#e2c990" stroke-width="1.6" pathLength="1"/>
    <rect class="mirror-fog" x="137" y="80" width="526" height="740" fill="url(#${id}-fog)"/>
    <path class="mirror-sweep" d="M-350 0H-70L370 900H90Z" fill="url(#${id}-sweep)"/>
    <path d="M149 300C149 169 251 94 400 94" fill="none" stroke="#f1f4d3" stroke-opacity=".24"/>
  </g>
  <path d="M114 833H686" stroke="#e3d5aa" stroke-opacity=".3"/><text class="mirror-engraving" x="400" y="862" text-anchor="middle" font-family="monospace" font-size="9" letter-spacing="6" fill="#b6a079">FEITO COM INTENÇÃO</text>
  </svg>`;
}
