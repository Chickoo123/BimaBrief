/* Feature 1: insurer evidence profiles with explicit scope and comparability states. */
(function(){
  "use strict";
  var I = IRC.I; if (!I) return;
  var $ = IRC.$, fmt = IRC.fmt, esc = IRC.esc, Y = "2024-25";
  var byId = {}; I.insurers.forEach(function(p){ byId[p.id] = p; });
  var TYPE = {public:"Public sector general insurer", private:"Private general insurer", standalone_health:"Stand-alone health insurer", specialised:"Specialised insurer"};
  var place = "All India";
  var list = I.insurers.filter(function(p){ var b = (p.business[Y] || {}).total; return b && b.gross_premium_lakh > 0; })
    .sort(function(a, b){ return a.name.localeCompare(b.name); });
  ["ins-a", "ins-b"].forEach(function(id, k){
    var sel = $(id);
    list.forEach(function(p){ var o = document.createElement("option"); o.value = p.id; o.textContent = p.name; sel.appendChild(o); });
    sel.value = k === 0 ? "icici-lombard" : "star";
    sel.addEventListener("change", render);
  });
  function years(p, key){ return Object.keys(p[key] || {}).sort(); }
  function missing(a,b,va,vb){
    var who = [];
    if (va == null) who.push(a.name);
    if (vb == null) who.push(b.name);
    return who.length ? {status:"blocked", why:"Cannot compare: a usable value is not available for " + who.join(" and ") + " in this view. Missing data is not zero."} : null;
  }
  function statusFor(ok, limited){ return !ok ? "blocked" : (limited ? "limited" : "comparable"); }
  function periodText(p, id){
    if (id === "solvency") {
      var s = p.solvency || [];
      return s.length ? "Quarterly observations · latest: " + s[s.length-1].q : "No quarterly series available";
    }
    if (id === "network") return "2024–25 snapshot · no annual trend";
    if (id === "complaints_per_10k") return "Annual series · complaint definitions vary by year";
    var key = id === "health_icr" ? "health" : id === "market_share" ? "business" : "claims_status";
    var n = years(p, key).length;
    return n ? "Annual series · " + n + " reported year(s)" : "No annual series available";
  }
  function sameScopeClaimStatus(a,b){
    if (a.claims_status_scope !== b.claims_status_scope) {
      var all = a.claims_status_scope === "all_lines" ? a : b;
      var health = a.claims_status_scope === "health_only" ? a : b;
      return {status:"blocked", why:"Not a health-to-health comparison. " + all.name + "’s figure includes multiple insurance lines (such as motor and fire); " + health.name + "’s figure is health-only. IRDAI does not provide the same health-only breakdown for this multi-line insurer."};
    }
    if (a.claims_status_scope === "all_lines") return {status:"limited", why:"Both figures cover all reported insurance lines, not health alone. This is an all-business comparison and cannot establish health-claim performance."};
    return {status:"comparable", why:"Both figures cover stand-alone health-insurer claims under the same Table 53 definition and reporting year. This is still an annual flow, not the rejection chance for newly filed claims."};
  }
  var M = [
    {id:"health_icr", label:"Health Incurred Claims Ratio (ICR)",
      get:function(p){ var t = ((p.health[Y] || {}).total || {}); return t.icr == null ? null : t.icr * 100; },
      show:function(v){ return v == null ? "Not available" : fmt(v,1) + "%"; },
      sub:function(p){ var t = ((p.health[Y] || {}).total || {}); return t.nep_lakh ? "Net earned health premium: ₹" + fmt(t.nep_lakh / 100) + " crore" : "Net earned premium not available"; },
      trend:function(p){ return Object.keys(p.health).sort().map(function(y){ var t = (p.health[y] || {}).total || {}; return t.icr == null ? null : t.icr * 100; }); }, ref:100,
      fair:function(a,b,va,vb){ var miss=missing(a,b,va,vb); if(miss)return miss;
        var small=[a,b].filter(function(p){var t=((p.health[Y]||{}).total||{});return !(t.nep_lakh>10000);});
        return small.length ? {status:"limited",why:"Same health-segment definition, but " + small.map(function(p){return p.name;}).join(" and ") + " is below our ₹100 crore earned-premium display threshold. A large claim can move a smaller base substantially. This is our caution rule, not an IRDAI statistical threshold."}
          : {status:"comparable",why:"Same health-segment ICR definition and financial year. ICR compares incurred claims with earned premium; it is not an approval rate or customer-service score."}; }},
    {id:"market_share", label:"Share of India’s health premium",
      get:function(p){ var t=((p.business[Y]||{}).total||{}); return t.market_share_pct == null ? null : t.market_share_pct; },
      show:function(v){ return v == null ? "Not available" : fmt(v,2) + "%"; },
      sub:function(p){var t=((p.business[Y]||{}).total||{});return t.policies != null ? fmt(t.policies) + " health policies in " + Y : "Policy count not reported";},
      trend:function(p){return Object.keys(p.business).sort().map(function(y){var t=((p.business[y]||{}).total||{});return t.market_share_pct == null ? null : t.market_share_pct;});},
      fair:function(a,b,va,vb){var miss=missing(a,b,va,vb);return miss||{status:"comparable",why:"Both values use the same insurer share of the reported Indian health-premium market in the same year. Market share is scale, not claim quality."};}},
    {id:"solvency", label:"Solvency ratio (whole company)",
      get:function(p){return p.solvency.length ? p.solvency[p.solvency.length-1].v : null;},
      show:function(v){return v == null ? "Not available" : fmt(v,2);},
      sub:function(p){return p.solvency.length ? "Latest reported quarter: " + p.solvency[p.solvency.length-1].q + ". IRDAI minimum: 1.50" : "No quarterly value reported";},
      trend:function(p){return p.solvency.slice(-12).map(function(s){return s.v;});}, ref:1.5,
      fair:function(a,b,va,vb){var miss=missing(a,b,va,vb);if(miss)return miss;var qa=a.solvency.length?a.solvency[a.solvency.length-1].q:"", qb=b.solvency.length?b.solvency[b.solvency.length-1].q:"";
        return qa===qb ? {status:"comparable",why:"Same latest reported quarter. Solvency is a whole-company measure, not health-only financial strength. IRDAI’s stated minimum is 1.50."}
          : {status:"limited",why:"Latest reported quarters differ ("+a.name+": "+(qa||"not reported")+"; "+b.name+": "+(qb||"not reported")+"). Treat the figures as separate snapshots, not a strict same-date ranking."};}},
    {id:"repudiated_pct", label:"Claims repudiated (% of claims decided)",
      get:function(p){var c=p.claims_status[Y]||{};return c.repudiated_pct == null ? null : c.repudiated_pct;},
      show:function(v){return v == null ? "Not available" : fmt(v,1) + "%";},
      sub:function(p){var c=p.claims_status[Y]||{};return c.decided ? fmt(c.decided) + " paid + repudiated + closed claims. " + (p.claims_status_scope==="health_only"?"Health only.":"All products, including other lines.") : "Denominator not available";},
      trend:function(p){return Object.keys(p.claims_status).sort().map(function(y){return p.claims_status[y].repudiated_pct;});},
      fair:function(a,b,va,vb){var miss=missing(a,b,va,vb);return miss||sameScopeClaimStatus(a,b);}},
    {id:"pending_pct", label:"Year-end outstanding share of claims workload",
      get:function(p){var c=p.claims_status[Y]||{};return c.pending_pct == null ? null : c.pending_pct;},
      show:function(v){return v == null ? "Not available" : fmt(v,1) + "%";},
      sub:function(p){var c=p.claims_status[Y]||{};return c.os_end != null ? fmt(c.os_end)+" outstanding at year-end ÷ (opening outstanding + new claims intimated). " + (p.claims_status_scope==="health_only"?"Health only.":"All products.") : "Source denominator or value unavailable";},
      trend:function(p){return Object.keys(p.claims_status).sort().map(function(y){return p.claims_status[y].pending_pct;});},
      fair:function(a,b,va,vb){var miss=missing(a,b,va,vb);return miss||sameScopeClaimStatus(a,b);}},
    {id:"complaints_per_10k", label:"All-product complaints per 10,000 health policies",
      get:function(p){var c=p.complaints[Y]||{};return c.per_10k_health_policies == null ? null : c.per_10k_health_policies;},
      show:function(v){return v == null ? "Not available" : fmt(v,1);},
      sub:function(p){var c=p.complaints[Y]||{};return c.new != null ? fmt(c.new)+" new reported complaints in "+Y+" (all products)" : "Raw complaint count not reported";},
      trend:function(p){var ys=Object.keys(p.complaints).sort(), prev=null;return ys.map(function(y){var c=p.complaints[y], value=c.per_10k_health_policies;var changed=prev!==null&&prev!==c.definition;prev=c.definition;return changed?null:value;});},
      fair:function(a,b,va,vb){var multi=[a,b].filter(function(p){return p.type!=="standalone_health";});
        if(multi.length)return {status:"blocked",why:"Not calculated for "+multi.map(function(p){return p.name;}).join(" and ")+": complaints include all products, while the denominator is health policies. The raw complaint counts are shown separately, not as a rate."};
        var miss=missing(a,b,va,vb);return miss||{status:"limited",why:"Both are stand-alone health insurers, but complaints include all reported products while the denominator is health policies. This is a rough context indicator, not an exact health-complaint rate or ranking."};}},
    {id:"network", label:"Network providers listed by IRDAI", trendLabel:"2024–25 snapshot",
      get:function(p){if(place!=="All India"&&!Object.prototype.hasOwnProperty.call(p.network||{},place))return null;if(place==="All India"&&!p.network_reported)return null;var n=place==="All India"?p.network_total:p.network[place];return n?(Number(n.direct||0)+Number(n.tpa||0)):null;},
      show:function(v){return v == null ? "Not reported" : fmt(v);},
      sub:function(p){if(place!=="All India"&&!Object.prototype.hasOwnProperty.call(p.network||{},place))return "No value reported for "+place+" in Table 80";if(place==="All India"&&!p.network_reported)return "No national provider total reported";var n=place==="All India"?p.network_total:p.network[place],t=(n.direct||0)+(n.tpa||0);return (place==="All India"?"Across India":"In "+place)+" · "+fmt(n.direct||0)+" direct, "+fmt(n.tpa||0)+" through TPAs";},
      trend:function(){return [];},
      fair:function(a,b,va,vb){var miss=missing(a,b,va,vb);return miss||{status:"limited",why:"Same source and reporting year, but a provider count is not a measure of service quality or guaranteed cashless access. The same provider may be listed by several insurers."};}}
  ];
  var META=I.metrics, metaKey={health_icr:"health_icr",market_share:"market_share",solvency:"solvency",repudiated_pct:"repudiated_pct",pending_pct:"pending_pct",complaints_per_10k:"complaints_per_10k",network:"network"};
  function head(p, tag){
    return '<div class="ins-head"><b>'+esc(p.name)+'</b><span class="type">'+esc(TYPE[p.type]||p.type)+'</span>'+(p.event?'<p class="event">'+esc(p.event)+'</p>':"")+p.flags.map(function(f){return '<div class="flag '+esc(f.level)+'">'+esc(f.text)+'<small>Rule: '+esc(f.rule)+'</small></div>';}).join("")+"</div>";
  }
  function render(){
    var a=byId[$("ins-a").value], b=byId[$("ins-b").value];
    $("ins-heads").innerHTML=head(a,"A")+head(b,"B");
    $("ins-rows").innerHTML=M.map(function(m,i){
      var va=m.get(a),vb=m.get(b),f=m.fair(a,b,va,vb),meta=META[metaKey[m.id]]||{}, blocked=f.status==="blocked";
      function cell(p,v,tag){
        var t=m.trend(p),spark=IRC.spark(t,{ref:m.ref});
        var period=m.trendLabel||periodText(p,m.id);
        return '<div class="value-card"><span class="value-owner">Company '+tag+' · '+esc(p.name)+'</span><span class="val">'+esc(m.show(v))+'<small>'+esc(m.sub(p))+'</small></span>'+(spark?'<span class="spark-period">'+esc(period)+'</span>'+spark:'<span class="spark-period">'+esc(period)+'</span>')+'</div>';
      }
      var label=m.label;
      return '<div class="mrow '+(blocked?'blocked':'')+'"><div class="lab"><b>'+esc(label)+'</b><button type="button" data-audit="'+i+'" aria-expanded="false">Source &amp; formula</button></div>'+
        '<div class="compare-values '+(blocked?'blocked-values':'')+'">'+cell(a,va,"A")+cell(b,vb,"B")+'</div>'+
        '<div class="verdict '+(f.status==='comparable'?'ok':f.status==='limited'?'limited':'no')+'"><strong>'+({comparable:"COMPARABLE",limited:"LIMITED COMPARISON",blocked:"NOT COMPARABLE"}[f.status]||"CHECK SCOPE")+'</strong> · '+esc(f.why)+'</div>'+
        '<div class="audit" id="audit-'+i+'" hidden><strong>'+esc(meta.table||"IRDAI source")+'</strong><br>'+esc(meta.formula||"")+(meta.note?'<br>'+esc(meta.note):"")+'<br>Source: IRDAI Handbook on Indian Insurance Statistics 2024–25. See the full table and source workbook via the About the Data section.</div></div>';
    }).join("");
    document.querySelectorAll("[data-audit]").forEach(function(btn){btn.addEventListener("click",function(){var el=$("audit-"+btn.dataset.audit);el.hidden=!el.hidden;btn.setAttribute("aria-expanded",String(!el.hidden));});});
  }
  IRC.onPlaceChange(function(p){place=p;render();});
  render();
})();
