/* Feature 2: Claim Journey Explorer, built from IRDAI Handbook Table 66. */
(function(){
  "use strict";
  var C=IRC.C; if(!C||!C.years)return;
  var $=IRC.$, esc=IRC.esc, years=C.meta.years.slice().reverse();
  var agingType="paid";
  var yearSel=$("claim-year"), routeSel=$("claim-route"), unitSel=$("claim-unit"), catSel=$("claim-category");
  years.forEach(function(y){var o=document.createElement("option");o.value=y;o.textContent=y.replace("-","–");yearSel.appendChild(o);});
  yearSel.value=C.meta.latest_year;
  var CAT_LABEL={cashless:"Only cashless",reimbursement:"Only reimbursement",both_cashless_and_reimbursement:"Both cashless and reimbursement",benefit_based:"Benefit-based",total:"All claims in this route"};
  var FLOW=[
    {key:"opening",label:"Outstanding at start",icon:"◷",meta:"Opening stock"},
    {key:"new_registered",label:"New claims registered",icon:"＋",meta:"Activity during the year"},
    {key:"paid",label:"Claims paid",icon:"✓",meta:"Paid during the year"},
    {key:"repudiated",label:"Claims repudiated",icon:"×",meta:"Repudiated during the year"},
    {key:"closing",label:"Outstanding at year-end",icon:"◷",meta:"Closing stock"}
  ];
  function routeLabel(k){return {all:"All claims",tpa:"Through TPAs",direct:"Handled directly by insurers"}[k]||k;}
  function categoryLabel(k){if(yearSel.value==="2015-16"&&getRoute()!=="all"){if(k==="cashless")return "Cashless";if(k==="reimbursement")return "Reimbursement";}return CAT_LABEL[k]||k;}
  function unitLabel(){return unitSel.value==="count"?"Claim count":"Amount in ₹ crore (converted from source ₹ lakh)";}
  function formatCount(v){
    if(v==null)return "Not reported";
    return Number(v).toLocaleString("en-IN",{maximumFractionDigits:1,minimumFractionDigits:(Math.abs(v%1)>0.00001?1:0)});
  }
  function formatValue(v){
    if(v==null)return "Not reported";
    if(unitSel.value==="amount_lakh")return "₹"+(Number(v)/100).toLocaleString("en-IN",{maximumFractionDigits:2,minimumFractionDigits:0})+" cr";
    return formatCount(v);
  }
  function unitKey(){return unitSel.value;}
  function getYear(){return C.years[yearSel.value];}
  function getRoute(){return routeSel.value;}
  function getCategory(){return catSel.value||"total";}
  function selected(){
    var yr=getYear(), rt=getRoute(), cat=getCategory();
    var route=yr.routes[rt]||{};
    return {year:yr,route:route,category:(route.categories||{}).total && rt==="all" ? route.categories.total : ((route.categories||{})[cat] || route.categories.total || null)};
  }
  function updateCategories(){
    var rt=getRoute(), yr=getYear(), route=yr.routes[rt]||{}, keys=Object.keys(route.categories||{});
    var old=catSel.value;
    catSel.innerHTML="";
    keys.forEach(function(k){var o=document.createElement("option");o.value=k;o.textContent=categoryLabel(k);catSel.appendChild(o);});
    catSel.value=keys.indexOf(old)>=0?old:(keys.indexOf("total")>=0?"total":keys[0]);
    catSel.disabled=rt==="all";
    catSel.setAttribute("aria-disabled",String(catSel.disabled));
  }
  function reconciliationMessage(sel){
    var unit=unitKey(),route=getRoute(),flow=sel.category?sel.category.flows:{};
    function val(k){return (flow[k]||{})[unit];}
    var keys=["opening","new_registered","paid","repudiated","closing"];
    var values=keys.map(val);
    if(values.some(function(v){return v==null;}))return {warning:true,text:"The source does not provide every component needed to check a simple annual flow equation. Values are shown as reported; no missing component is filled in."};
    var residual=values[0]+values[1]-values[2]-values[3]-values[4];
    if(unit==="amount_lakh"){
      var da=(flow.disallowed||{}).amount_lakh;
      if(da!=null)residual-=da;
      else if(Math.abs(residual)>0.01)return {warning:true,text:"The reported amount components do not reconcile under the simple opening + new claims − paid − repudiated − closing equation. The source does not report a usable ‘claims disallowed’ amount for this view. Figures are preserved as published; no balancing adjustment is made."};
    }
    if(Math.abs(residual)>(unit==="count"?0.5:0.01)){
      return {warning:true,text:"The source figures do not fully reconcile under this simple annual flow check (difference: "+(unit==="count"?formatCount(residual):"₹"+(residual/100).toLocaleString("en-IN",{maximumFractionDigits:2})+" crore")+"). This is an audit warning, not a correction. Reported values remain unchanged."};
    }
    return {warning:false,text:"The selected figures reconcile within the display tolerance used for source rounding. That does not mean the same individual claims are followed from registration to outcome."};
  }
  function renderSummary(sel){
    $("claim-summary").innerHTML='<span class="summary-pill"><i></i>'+esc(yearSel.value)+'</span><span class="summary-pill">Industry-level totals</span><span class="summary-pill">'+esc(routeLabel(getRoute()))+'</span><span class="summary-pill">Health insurance excluding personal accident and travel</span>';
    $("claim-unit-label").textContent=unitSel.value==="count"?"Claim count":"Amount · ₹ crore";
    $("claim-limitations").innerHTML='<div class="limit-card"><strong>Not one claim cohort</strong>Claims paid or repudiated during the year may have been registered in an earlier year.</div><div class="limit-card"><strong>Count ≠ amount</strong>A count tells how many claims were reported; amount tells the money involved. They are shown separately.</div><div class="limit-card"><strong>Industry, not insurer</strong>Table 66 does not identify company-specific claim speed or outcomes.</div><div class="limit-card"><strong>Values as published</strong>Some duration-bucket claim counts are fractional in the source; the screen rounds for readability, while the stored source values remain unchanged.</div>';
  }
  function renderFlow(sel){
    var flow=sel.category?sel.category.flows:{};
    var cards=FLOW.map(function(f){var v=(flow[f.key]||{})[unitKey()];return '<div class="flow-card" data-flow="'+f.key+'"><span class="flow-icon" aria-hidden="true">'+f.icon+'</span><span class="flow-label">'+f.label+'</span><span class="flow-value">'+formatValue(v)+'</span><span class="flow-meta">'+f.meta+'</span></div>';});
    var disallowed=(flow.disallowed||{})[unitKey()];
    if(unitKey()==="amount_lakh"){
      cards.push('<div class="flow-card" data-flow="disallowed"><span class="flow-icon" aria-hidden="true">≠</span><span class="flow-label">Claims disallowed amount</span><span class="flow-value">'+formatValue(disallowed)+'</span><span class="flow-meta">Reported separately; not a claim count</span></div>');
    }
    $("claim-flow").innerHTML=cards.join("");
    var recon=reconciliationMessage(sel), el=$("claim-discrepancy");
    el.hidden=!recon.warning;el.textContent=recon.text;
    if(!recon.warning){el.hidden=false;el.className="claim-discrepancy good";el.textContent=recon.text;}
    else el.className="claim-discrepancy";
  }
  function renderAging(sel){
    var a=sel.category && sel.category.aging ? sel.category.aging[agingType] : null;
    var el=$("claim-aging");
    if(!a||!a.length){el.innerHTML='<p class="note">Aging data is not available for this category and financial year. It is left unavailable rather than estimated.</p>';$("claim-aging-note").textContent="";return;}
    var vals=a.map(function(x){return x[unitKey()];}), valid=vals.filter(function(v){return v!=null&&v>=0;}), total=valid.reduce(function(s,v){return s+v;},0), max=Math.max.apply(null,valid.concat([0]));
    el.innerHTML=a.map(function(bucket,i){
      var v=vals[i], share=(v!=null&&total>0)?v/total*100:null, width=(v!=null&&max>0)?Math.max(0,v/max*100):0;
      return '<div class="aging-row"><span class="aging-label">'+esc(bucket.label)+'</span><div class="aging-track" role="img" aria-label="'+esc(bucket.label)+': '+esc(formatValue(v))+'"><div class="aging-fill" style="width:'+width+'%"></div></div><span class="aging-value">'+formatValue(v)+(share==null?'':' <span class="aging-share">'+share.toLocaleString("en-IN",{maximumFractionDigits:1})+'%</span>')+'</span></div>';
    }).join("");
    var note=C.meta.aging_notes[agingType]||"";
    var shareNote=unitKey()==="count"?"Percentage is each bucket’s share of the sum of reported aging buckets, not claim approval probability.":"Percentage is each bucket’s share of the sum of reported aging amounts; displayed amounts are converted from ₹ lakh to ₹ crore.";
    $("claim-aging-note").textContent=note+" "+shareNote;
  }
  function render(){
    updateCategories();
    var sel=selected();
    renderSummary(sel);renderFlow(sel);renderAging(sel);
  }
  yearSel.addEventListener("change",render);
  routeSel.addEventListener("change",render);
  unitSel.addEventListener("change",render);
  catSel.addEventListener("change",render);
  document.querySelectorAll("[data-aging]").forEach(function(btn){btn.addEventListener("click",function(){agingType=btn.dataset.aging;document.querySelectorAll("[data-aging]").forEach(function(b){b.setAttribute("aria-pressed",String(b===btn));});render();});});
  render();
})();
