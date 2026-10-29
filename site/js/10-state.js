(function(){
  "use strict";
  var D = IRC.D;
  if (!D) {
    document.getElementById("hero").textContent = "This is the template file, so it has no data. Open docs/index.html to see the website.";
    return;
  }
  var SEG = "individual";
  var LABEL = {individual:"individual and family policy segment", group:"employer and group cover segment", government:"government-scheme segment"};
  var INR = new Intl.NumberFormat("en-IN", {maximumFractionDigits:0});
  var places = Object.keys(D.states).filter(function(s){return s !== "All India";}).sort();
  var years = Object.keys(D.states["All India"]).sort();
  var $ = function(id){return document.getElementById(id);};

  function crore(lakh){
    if (lakh == null) return "an amount that is not available";
    var c = lakh / 100;
    return "₹" + (Math.abs(c) >= 100 ? INR.format(c) : c.toLocaleString("en-IN",{maximumFractionDigits:1})) + " crore";
  }
  function get(place, year, seg){ var y = (D.states[place]||{})[year]; return y ? y[seg] : null; }
  function ratio(d){
    if (!d || d.gross_premium_lakh == null || d.claims_paid_lakh == null) return null;
    if (d.gross_premium_lakh <= 0 || d.claims_paid_lakh < 0 || d.has_negative_component) return null;
    return d.claims_paid_lakh / d.gross_premium_lakh * 100;
  }
  function eligible(d, seg){
    if (!d) return false;
    if (seg === "individual") return (d.policies||0) >= 50000;
    if (seg === "group") return (d.persons_covered_thousand||0) >= 100;
    return false;
  }

  // controls
  var placeSel = $("place"), yearSel = $("year");
  ["All India"].concat(places).forEach(function(p){ var o = document.createElement("option"); o.value = o.textContent = p; placeSel.appendChild(o); });
  years.slice().reverse().forEach(function(y){ var o = document.createElement("option"); o.value = o.textContent = y; yearSel.appendChild(o); });
  var jar = $("jar");

  // Shareable state snapshots: preserve the selected state, year and segment in the URL.
  // Unknown or invalid query values are ignored rather than producing an empty view.
  function applySharedView(){
    var params = new URLSearchParams(window.location.search);
    var sharedPlace = params.get("state"), sharedYear = params.get("year"), sharedSeg = params.get("cover");
    if (sharedPlace && Array.from(placeSel.options).some(function(o){ return o.value === sharedPlace; })) placeSel.value = sharedPlace;
    if (sharedYear && Array.from(yearSel.options).some(function(o){ return o.value === sharedYear; })) yearSel.value = sharedYear;
    if (["individual", "group", "government"].indexOf(sharedSeg) >= 0) SEG = sharedSeg;
    document.querySelectorAll(".seg button").forEach(function(b){ b.setAttribute("aria-pressed", b.dataset.seg === SEG ? "true" : "false"); });
  }
  function syncSharedView(){
    try {
      var url = new URL(window.location.href);
      url.searchParams.set("state", placeSel.value || "All India");
      url.searchParams.set("year", yearSel.value || years[years.length - 1]);
      url.searchParams.set("cover", SEG);
      window.history.replaceState({}, "", url.toString());
    } catch (e) { /* file preview or restricted browser: sharing still uses the current URL */ }
  }
  function copyShareLink(){
    var shareUrl;
    try {
      var url = new URL(window.location.href);
      url.searchParams.set("state", placeSel.value || "All India");
      url.searchParams.set("year", yearSel.value || years[years.length - 1]);
      url.searchParams.set("cover", SEG);
      shareUrl = url.toString();
    } catch (e) { shareUrl = window.location.href; }
    var status = $("share-status"), btn = $("share-snapshot");
    function done(ok){
      status.textContent = ok ? "Link copied — it opens this same view." : "Copy this page URL and include state=" + encodeURIComponent(placeSel.value) + "&year=" + yearSel.value + "&cover=" + SEG;
      if (ok) { btn.textContent = "✓ Link copied"; window.setTimeout(function(){ btn.textContent = "↗ Copy shareable view"; }, 2200); }
    }
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(shareUrl).then(function(){ done(true); }).catch(function(){ fallbackCopy(shareUrl); });
    } else fallbackCopy(shareUrl);
    function fallbackCopy(text){
      var ta = document.createElement("textarea"); ta.value = text; ta.setAttribute("readonly", "");
      ta.style.position = "fixed"; ta.style.opacity = "0"; document.body.appendChild(ta); ta.select();
      var ok = false; try { ok = document.execCommand("copy"); } catch (e) { ok = false; }
      ta.remove(); done(ok);
    }
  }
  applySharedView();

  function displayRatio(v){ return v == null ? "Not available" : v.toLocaleString("en-IN", {maximumFractionDigits:1, minimumFractionDigits: v % 1 ? 1 : 0}); }

  function render(){
    var place = placeSel.value, year = yearSel.value, d = get(place, year, SEG), r = ratio(d);
    $("h-place").textContent = place;
    $("card-year").textContent = year.replace("-", "–");
    $("h-prem").textContent = d ? crore(d.gross_premium_lakh) : "an amount that is not available";
    $("h-claims").textContent = d ? crore(d.claims_paid_lakh) : "an amount that is not available";
    $("h-who").textContent = LABEL[SEG];

    // Use a scalable track with a visible ₹100 benchmark. Values above ₹100 extend beyond
    // that benchmark instead of disappearing at the old 100-box limit.
    var axisMax = r == null ? 100 : (r > 100 ? Math.ceil(r / 50) * 50 : 100);
    var markerAt = 100 / axisMax * 100;
    var fillAt = r == null ? 0 : Math.min(100, r / axisMax * 100);
    jar.innerHTML = r == null ? '<span class="ratio-marker" style="--mark-at:' + markerAt + '%"></span>' :
      '<span class="ratio-fill" style="width:' + fillAt + '%"></span><span class="ratio-marker" style="--mark-at:' + markerAt + '%"></span>' ;
    jar.setAttribute("aria-label", r == null ? "Ratio unavailable" : "Claims paid per 100 of premium: " + displayRatio(r) + "; scale ends at " + axisMax);
    $("ratio-axis").innerHTML = axisMax > 100
      ? '<span>₹0</span><span>₹100 benchmark</span><span>₹' + axisMax + '</span>'
      : '<span>₹0</span><span>₹50</span><span>₹100 benchmark</span>' ;
    $("big").innerHTML = r == null
      ? 'Not available<small>' + (d && d.has_negative_component ? 'One or more source components are negative accounting adjustments. The project does not calculate a ratio from this combination.' : 'The reported figures do not support a fair calculation for this selection.') + '</small>'
      : '₹' + displayRatio(r) + ' per ₹100<small>Claims paid in ' + year + ' compared with premium reported in the same year. This is not an individual claim approval chance, ICR, CSR or profit measure.</small>' ;
    var note = '';
    if (SEG === "government") note = '<p class="note">Government schemes have different funding and accounting structures. Some source values are negative adjustments, so this segment is shown for context and is not ranked across states.</p>' ;
    $("seg-note").innerHTML = note;
    $("facts").innerHTML = d ? [
      ["Policies issued", d.policies == null ? "Not available" : INR.format(d.policies)],
      ["Persons covered", d.persons_covered_thousand == null ? "Not available" : INR.format(d.persons_covered_thousand * 1000)],
      ["Claims paid", d.claims_paid_count == null ? "Not available" : INR.format(d.claims_paid_count)]
    ].map(function(f){ return "<div><b>" + f[1] + "</b>" + f[0] + "</div>"; }).join("") : "";
    renderStrip(place, year); renderTrend(place); renderCash(place); IRC.emitPlace(place); syncSharedView();
  }

  function renderStrip(place, year){
    var strip = $("strip"); strip.innerHTML = ""; var noteEl = $("cmp-note"); noteEl.innerHTML = "";
    var axis = document.querySelector("#state-comparison .axis");
    if (SEG === "government") {
      $("cmp-lede").textContent = "Government schemes are not ranked across states because their funding and accounting structures differ.";
      strip.innerHTML = '<p class="note">State comparison unavailable for this segment.</p>';
      if (axis) axis.innerHTML = "";
      return;
    }
    var rule = SEG === "individual" ? "at least 50,000 policies" : "at least 1 lakh people covered";
    var pts = places.map(function(p){ var d = get(p, year, SEG); return {p:p, d:d, r:ratio(d)}; })
      .filter(function(x){ return x.r != null && eligible(x.d, SEG); })
      .sort(function(a,b){ return b.r - a.r; });
    $("cmp-lede").textContent = "Claims paid per ₹100 of premium in " + year + ", using the same definition for each included state or UT. Display rule: " + rule + ". The threshold is a presentation choice, not a statistical guarantee.";
    var maxObserved = pts.reduce(function(m,x){return Math.max(m,x.r);}, 0);
    var scaleMax = Math.max(150, Math.ceil(maxObserved / 50) * 50);
    if (axis) axis.innerHTML = '<span>₹0</span><span>₹50</span><span>₹100</span><span>₹' + scaleMax + ' scale max</span>';
    pts.forEach(function(x){
      var row = document.createElement("div"); row.className = "state-line" + (x.p === place ? " selected" : "");
      var name = document.createElement("span"); name.className = "state-name"; name.textContent = x.p + (x.p === place ? " · selected" : "");
      var track = document.createElement("div"); track.className = "state-track"; track.setAttribute("aria-hidden", "true");
      var fill = document.createElement("div"); fill.className = "state-fill"; fill.style.width = Math.min(100, x.r / scaleMax * 100) + "%"; track.appendChild(fill);
      var value = document.createElement("span"); value.className = "state-value"; value.textContent = "₹" + displayRatio(x.r);
      row.appendChild(name); row.appendChild(track); row.appendChild(value); strip.appendChild(row);
    });
    var ai = ratio(get("All India", year, SEG));
    if (ai != null) noteEl.innerHTML += '<p class="note"><strong>All India reference:</strong> ₹' + displayRatio(ai) + ' per ₹100. A national figure is not the simple average of state ratios.</p>';
    var mine = pts.filter(function(x){return x.p === place;})[0];
    if (place !== "All India" && !mine) noteEl.innerHTML += '<p class="note">' + IRC.esc(place) + " is not included in this comparison for " + year + " because it does not meet the display rule or its ratio is not available. Its reported figures remain available in the state selector.</p>";
    noteEl.innerHTML += '<details class="all-states"><summary>How to read this comparison</summary><p>Each bar uses the same horizontal scale for the selected year. These are same-year claims-paid-to-premium ratios, not claim approval rates or measures of insurer quality.</p></details>';
  }

  function renderTrend(place){
    var svg = $("trend"), W = 700, H = 260, L = 44, R = 16, T = 16, B = 34;
    var series = [{name:"All India", c:"var(--muted)", w:2}];
    if (place !== "All India") series.unshift({name:place, c:"var(--mark)", w:3});
    var all = [];
    series.forEach(function(s){ s.v = years.map(function(y){ return ratio(get(s.name, y, SEG)); }); all = all.concat(s.v.filter(function(v){return v != null;})); });
    var max = Math.max(120, Math.ceil((Math.max.apply(null, all.length ? all : [100]) + 10) / 20) * 20);
    var x = function(i){ return L + i * (W - L - R) / (years.length - 1); }, y = function(v){ return T + (1 - v / max) * (H - T - B); };
    var out = "";
    for (var g = 0; g <= max; g += max > 200 ? 50 : 20) out += '<line x1="' + L + '" x2="' + (W - R) + '" y1="' + y(g) + '" y2="' + y(g) + '" stroke="var(--line)"/><text x="' + (L - 8) + '" y="' + (y(g) + 4) + '" text-anchor="end">₹' + g + "</text>";
    out += '<line x1="' + L + '" x2="' + (W - R) + '" y1="' + y(100) + '" y2="' + y(100) + '" stroke="var(--ink)" stroke-dasharray="4 4" opacity=".5"/>';
    years.forEach(function(yy, i){ if (i % 2 === 0 || i === years.length - 1) out += '<text x="' + x(i) + '" y="' + (H - 10) + '" text-anchor="middle">' + yy + "</text>"; });
    series.forEach(function(s){
      var path = "", pen = false;
      s.v.forEach(function(v, i){ if (v == null) { pen = false; return; } path += (pen ? "L" : "M") + x(i).toFixed(1) + " " + y(Math.min(v, max)).toFixed(1) + " "; pen = true; });
      out += '<path d="' + path + '" fill="none" stroke="' + s.c + '" stroke-width="' + s.w + '" stroke-linejoin="round"/>';
      s.v.forEach(function(v, i){ if (v != null) out += '<circle cx="' + x(i) + '" cy="' + y(Math.min(v, max)) + '" r="3.5" fill="' + s.c + '"><title>' + s.name + " " + years[i] + ": ₹" + Math.round(v) + "</title></circle>"; });
    });
    var ci = years.indexOf("2021-22");
    if (ci >= 0) out += '<text x="' + x(ci) + '" y="' + (T + 10) + '" text-anchor="middle">COVID-19 second wave year</text>';
    svg.innerHTML = out;
    $("trend-legend").innerHTML = series.map(function(s){ return '<span style="--c:' + s.c + '">' + s.name + "</span>"; }).join("") + '<span style="--c:var(--ink)">₹100 line (claims equal premium)</span>';
  }

  function renderCash(place){
    var bar = $("cash-bar"), lede = $("cash-lede"), noteEl = $("cash-note"); noteEl.innerHTML = ""; bar.innerHTML = ""; $("cash-legend").innerHTML = "";
    if (SEG === "government") { lede.textContent = "IRDAI does not publish this split for government schemes."; return; }
    var cy = Object.keys((D.cashless[place] || {})).sort(), yr = cy.indexOf(yearSel.value) >= 0 ? yearSel.value : cy[cy.length - 1];
    var c = yr ? ((D.cashless[place] || {})[yr] || {})[SEG] : null;
    if (!c || c.cashless_share_pct == null) { lede.textContent = "Not available for " + place + "."; return; }
    var parts = [["Cashless", c.cashless, "var(--paid)"], ["Reimbursement", c.reimbursement, "var(--muted)"], ["Partly both", c.both, "var(--mark)"], ["Fixed benefit", c.benefit, "var(--kept)"]];
    var tot = c.parts_total;
    lede.textContent = "In " + yr + ", " + c.cashless_share_pct.toFixed(0) + " of every 100 paid claims in " + place + " were settled cashless, where the insurer pays the hospital directly. The rest were reimbursed after the patient paid, partly cashless and partly reimbursed, or paid as a fixed benefit (see the split below). This counts paid claims only, so it is not an approval rate, and it also depends on how many network hospitals are nearby." + (yr !== yearSel.value ? " (This split is only published from 2020-21.)" : "");
    parts.forEach(function(p){ if (p[1] > 0) { var d = document.createElement("div"); d.style.width = (p[1] / tot * 100) + "%"; d.style.background = p[2]; d.title = p[0] + ": " + INR.format(p[1]); bar.appendChild(d); } });
    $("cash-legend").innerHTML = parts.map(function(p){ return '<span style="--c:' + p[2] + '">' + p[0] + " " + (tot ? Math.round(p[1] / tot * 100) : 0) + "%</span>"; }).join("");
    if (c.total_mismatch) noteEl.innerHTML = '<p class="note">In IRDAI’s table, the “Total” for ' + place + " in " + yr + " does not equal the sum of its parts (" + INR.format(c.total) + " vs " + INR.format(c.parts_total) + "). The split above uses the parts.</p>";
  }

  document.querySelectorAll(".seg button").forEach(function(b){
    b.addEventListener("click", function(){
      SEG = b.dataset.seg;
      document.querySelectorAll(".seg button").forEach(function(o){ o.setAttribute("aria-pressed", o === b ? "true" : "false"); });
      render();
    });
  });
  placeSel.addEventListener("change", render); yearSel.addEventListener("change", render);
  if ($("share-snapshot")) $("share-snapshot").addEventListener("click", copyShareLink);
  $("built").textContent = "Data: " + D.meta.source + " (latest year " + D.meta.latest_year + "). Site last rebuilt on " + D.meta.built_on + ".";
  if (D.meta.repo_url) { $("gh").href = D.meta.repo_url; var correction = $("correction-link"); if (correction) correction.href = D.meta.repo_url.replace(/\/$/, "") + "/issues/new?template=data-correction.yml"; } else { $("gh").hidden = true; var correction = $("correction-link"); if (correction) correction.hidden = true; }
  render();
})();
