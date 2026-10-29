/* Shared data + helpers. Every other module reads from window.IRC. */
window.IRC = (function(){
  "use strict";
  function read(id){
    var el = document.getElementById(id);
    try { return JSON.parse(el.textContent); } catch (e) { return null; }
  }
  var INR = new Intl.NumberFormat("en-IN", {maximumFractionDigits:0});
  return {
    D: read("app-data"),
    I: read("insurer-data"),
    C: read("claim-data"),
    INR: INR,
    $: function(id){ return document.getElementById(id); },
    fmt: function(v, d){ return v == null ? "Not available" : v.toLocaleString("en-IN", {maximumFractionDigits: d == null ? 0 : d, minimumFractionDigits: d || 0}); },
    esc: function(t){ return String(t).replace(/[&<>"]/g, function(c){ return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]; }); },
    listeners: [],
    onPlaceChange: function(fn){ this.listeners.push(fn); },
    emitPlace: function(p){ this.listeners.forEach(function(fn){ fn(p); }); },
    /* tiny SVG sparkline; ref = optional horizontal reference line */
    spark: function(vals, opt){
      opt = opt || {}; var W = opt.w || 160, H = opt.h || 36, P = 3;
      var v = vals.filter(function(x){ return x != null; });
      if (v.length < 2) return "";
      var lo = Math.min.apply(null, v.concat(opt.ref != null ? [opt.ref] : [])), hi = Math.max.apply(null, v.concat(opt.ref != null ? [opt.ref] : []));
      if (hi === lo) { hi += 1; lo -= 1; }
      var x = function(i){ return P + i * (W - 2 * P) / (vals.length - 1); }, y = function(t){ return H - P - (t - lo) / (hi - lo) * (H - 2 * P); };
      var d = "", pen = false;
      vals.forEach(function(t, i){ if (t == null) { pen = false; return; } d += (pen ? "L" : "M") + x(i).toFixed(1) + " " + y(t).toFixed(1) + " "; pen = true; });
      var ref = opt.ref != null ? '<line x1="0" x2="' + W + '" y1="' + y(opt.ref) + '" y2="' + y(opt.ref) + '" stroke="var(--warn-ink)" stroke-dasharray="3 3" opacity=".7"/>' : "";
      return '<svg class="spark" viewBox="0 0 ' + W + " " + H + '" width="' + W + '" height="' + H + '" aria-hidden="true">' + ref + '<path d="' + d + '" fill="none" stroke="currentColor" stroke-width="2"/></svg>';
    }
  };
})();
