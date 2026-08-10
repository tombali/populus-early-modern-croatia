(function(){
  "use strict";
  if(typeof DATA==="undefined"||!DATA)return;
  const $=id=>document.getElementById(id);
  const tip=$("tip");
  const TIER=[{k:"good",label:"Precise location"},
              {k:"warn",label:"Approximate (uncertain / fuzzy)"},
              {k:"crit",label:"No coordinates"}];
  const cssv=n=>getComputedStyle(document.documentElement)
                  .getPropertyValue(n).trim();
  const isDark=()=>document.documentElement.getAttribute("data-theme")==="dark"
      || (!document.documentElement.getAttribute("data-theme")
          && matchMedia("(prefers-color-scheme: dark)").matches);

  const byId={}; DATA.places.forEach(p=>byId[p[0]]={
    id:p[0],name:p[1],modern:p[2],cty:p[3],lat:p[4],lon:p[5],tier:p[6]});

  // ---- geographic projection (equirectangular) ------------------------
  let latMin=99,latMax=-99,lonMin=999,lonMax=-999;
  const grow=(lo,la)=>{latMin=Math.min(latMin,la);latMax=Math.max(latMax,la);
    lonMin=Math.min(lonMin,lo);lonMax=Math.max(lonMax,lo);};
  DATA.places.forEach(p=>grow(p[5],p[4]));
  // Frame by the core county mosaic only — Međimurje / Požega-Slavonia are
  // drawn for context but must not push the initial view past current edges.
  const NO_FRAME=new Set(["Međimurska županija","Požeško-slavonska županija"]);
  (DATA.geo.counties||[]).forEach(c=>{
    if(NO_FRAME.has(c.name))return;
    c.rings.forEach(r=>r.forEach(q=>grow(q[0],q[1])));
  });
  const pad=.05*(latMax-latMin);
  latMin-=pad;latMax+=pad;lonMin-=pad;lonMax+=pad;
  const midLat=(latMin+latMax)/2, kx=Math.cos(midLat*Math.PI/180);
  const geoW=(lonMax-lonMin)*kx, geoH=(latMax-latMin);
  const MW=1000, MH=Math.round(MW*geoH/geoW);
  const mapSvg=$("map");
  mapSvg.setAttribute("viewBox",`0 0 ${MW} ${MH}`);
  const px=lon=>((lon-lonMin)*kx)/geoW*MW;
  const py=lat=>(latMax-lat)/geoH*MH;

  // ---- scale bar ---------------------------------------------------------
  // geoW/MW is "kx-adjusted" degrees per viewBox unit; that adjustment (kx =
  // cos(midLat)) is exactly what makes 1 unit of longitude-at-this-latitude
  // equal 1 unit of latitude in real distance, so both axes share one
  // km-per-viewBox-unit constant (111.32 km/degree, the standard average).
  const KM_PER_DEG=111.32;
  const kmPerUnit=(geoW/MW)*KM_PER_DEG;
  const NICE=[1,2,5];
  function niceDistance(km){
    if(km<=0)return 0;
    const mag=Math.pow(10,Math.floor(Math.log10(km)));
    let best=mag,bestDiff=Infinity;
    for(const mult of [...NICE,10]){
      const cand=mult*mag, diff=Math.abs(cand-km);
      if(diff<bestDiff){bestDiff=diff;best=cand;}
    }
    return best;
  }
  const scaleBar=$("scale-bar"), scaleLabel=$("scale-label");
  function updateScale(){
    if(!scaleBar)return;
    const rectW=mapSvg.getBoundingClientRect().width||MW;
    const kmPerPx=(vb.w*kmPerUnit)/rectW;
    if(!isFinite(kmPerPx)||kmPerPx<=0)return;
    const niceKm=niceDistance(90*kmPerPx);   // target ≈90px-wide bar
    scaleBar.style.width=Math.max(2,niceKm/kmPerPx)+"px";
    scaleLabel.textContent=niceKm>=1?`${niceKm} km`:`${Math.round(niceKm*1000)} m`;
  }
  addEventListener("resize",updateScale);

  // ---- pan / zoom (viewBox) --------------------------------------------
  const vb0={x:0,y:0,w:MW,h:MH};
  let vb={...vb0};
  const MIN_Z=1, MAX_Z=32;
  function applyVB(){
    mapSvg.setAttribute("viewBox",`${vb.x} ${vb.y} ${vb.w} ${vb.h}`);
    updateScale();}
  function zoomAt(factor,cx,cy){
    const nx=vb.x+cx*vb.w, ny=vb.y+cy*vb.h;
    const nw=Math.min(Math.max(vb.w/factor,vb0.w/MAX_Z),vb0.w/MIN_Z);
    const nh=nw*vb0.h/vb0.w;
    vb.x=nx-cx*nw; vb.y=ny-cy*nh; vb.w=nw; vb.h=nh; applyVB();
    if(typeof closePopup==="function")closePopup();
    if(typeof drawMarkers==="function")drawMarkers();}   // keep marker size constant
  function resetView(){vb={...vb0};applyVB();
    if(typeof closePopup==="function")closePopup();
    if(typeof drawMarkers==="function")drawMarkers();}
  applyVB();
  mapSvg.addEventListener("wheel",ev=>{
    ev.preventDefault();
    const r=mapSvg.getBoundingClientRect();
    zoomAt(ev.deltaY<0?1.18:1/1.18,
      (ev.clientX-r.left)/r.width,(ev.clientY-r.top)/r.height);},
    {passive:false});
  let drag=null;
  mapSvg.addEventListener("pointerdown",ev=>{
    if(ev.button!==0)return;
    const t=ev.target;
    if(t!==mapSvg&&t.tagName!=="path"&&t.tagName!=="text")return;
    if(typeof closePopup==="function")closePopup();   // background click dismisses popup
    drag={x:ev.clientX,y:ev.clientY,vb:{...vb}}; mapSvg.classList.add("dragging");
    mapSvg.setPointerCapture(ev.pointerId);});
  mapSvg.addEventListener("pointermove",ev=>{
    if(!drag)return;
    const r=mapSvg.getBoundingClientRect();
    vb.x=drag.vb.x-(ev.clientX-drag.x)/r.width*drag.vb.w;
    vb.y=drag.vb.y-(ev.clientY-drag.y)/r.height*drag.vb.h;
    applyVB();});
  const endDrag=ev=>{
    if(!drag)return;
    drag=null; mapSvg.classList.remove("dragging");
    try{mapSvg.releasePointerCapture(ev.pointerId);}catch(_){}};
  mapSvg.addEventListener("pointerup",endDrag);
  mapSvg.addEventListener("pointercancel",endDrag);
  $("zoom-in").onclick=()=>zoomAt(1.4,.5,.5);
  $("zoom-out").onclick=()=>zoomAt(1/1.4,.5,.5);
  $("zoom-reset").onclick=resetView;

  const hiddenCounties=new Set();

  // ---- map size scale --------------------------------------------------
  let maxTax=1;
  Object.values(DATA.burden).forEach(a=>a.forEach(e=>maxTax=Math.max(maxTax,e[1])));
  // Marker radius by tax. Tax is clamped to a floor of 5 for sizing, so every
  // place with ≤5 selišta gets the same (5-selišta) size — the tiny 1–2 selišta
  // places are then as visible as a 5. Above 5 the size scales with √tax.
  // msizeMult is the user-controlled 1x–2x slider; rOf (used everywhere,
  // including cluster-spread math) always reflects the current setting.
  const SIZE_FLOOR=5;
  let msizeMult=1;
  const rBase=t=>1.8+16*Math.sqrt(Math.max(t,SIZE_FLOOR))/Math.sqrt(maxTax);
  const rOf=t=>rBase(t)*msizeMult;

  const SVGNS="http://www.w3.org/2000/svg";
  const el=(n,a)=>{const e=document.createElementNS(SVGNS,n);
    for(const k in a)e.setAttribute(k,a[k]);return e;};

  // shape encodes county (colour is reserved for confidence tier)
  const SHAPE={4:"circle",1:"square",2:"triangle",3:"diamond"};
  const SHAPEGLYPH={4:"●",1:"■",2:"▲",3:"◆"};
  function marker(cty,x,y,r,fill,op){
    // vector-effect keeps the separating outline a constant ~0.7 SCREEN px at
    // every zoom. Without it the stroke (in viewBox units) grows with the zoom
    // and, being the background colour, paints over the marker at deep zoom —
    // making markers vanish on the last zoom levels.
    const a={class:"marker",fill,"fill-opacity":op,stroke:cssv("--surface"),
             "stroke-width":.7,"vector-effect":"non-scaling-stroke"};
    const s=SHAPE[cty];
    if(s==="square"){const h=r*.85;
      return el("rect",Object.assign({x:x-h,y:y-h,width:2*h,height:2*h,rx:1},a));}
    if(s==="diamond"){const h=r*.92;
      return el("rect",Object.assign({x:x-h,y:y-h,width:2*h,height:2*h,rx:1,
        transform:`rotate(45 ${x} ${y})`},a));}
    if(s==="triangle"){const R=r*1.3;
      return el("polygon",Object.assign({points:
        `${x},${y-R} ${x+R*.866},${y+R*.5} ${x-R*.866},${y+R*.5}`},a));}
    return el("circle",Object.assign({cx:x,cy:y,r},a));
  }
  function showTip(html,ev){tip.innerHTML=html;tip.style.opacity=1;
    const x=ev.clientX,y=ev.clientY,w=tip.offsetWidth,h=tip.offsetHeight;
    tip.style.left=Math.min(x+14,innerWidth-w-8)+"px";
    tip.style.top=Math.max(y-h-12,8)+"px";}
  const hideTip=()=>tip.style.opacity=0;
  const fmt=n=>Math.round(n).toLocaleString("en");

  // ---- click popup (persistent location details) -----------------------
  const pop=document.createElement("div");
  pop.className="popup"; pop.setAttribute("role","dialog"); pop.hidden=true;
  document.body.appendChild(pop);
  function closePopup(){pop.hidden=true;}
  function popupHtml(r,tier,year){
    const p=r.p;
    const loc=p.tier===2
      ? `<div class="pc">No coordinates — placed near the county town</div>`
      : `<div class="pc">Coordinates ${(+p.lat).toFixed(4)}, ${(+p.lon).toFixed(4)}</div>`;
    return `<button class="popup-x" type="button" aria-label="Close">×</button>`
      +`<div class="pt">${p.name}</div>`
      +(p.modern?`<div class="pm">= ${p.modern}</div>`:"")
      +`<div class="pr">${DATA.counties[p.cty].name} county · ${year}</div>`
      +`<div class="pr">Taxable <b>${fmt(r.tax)}</b> selišta`
        +(r.ab>0?` · abandoned <b>${fmt(r.ab)}</b>`:"")+`</div>`
      +loc
      +`<div class="pc"><span class="dot" style="background:var(--${TIER[tier].k})">`
      +`</span>${TIER[tier].label}</div>`;
  }
  function showPopup(r,tier,year,ev){
    pop.innerHTML=popupHtml(r,tier,year);
    pop.hidden=false; hideTip();
    const w=pop.offsetWidth,h=pop.offsetHeight;
    let x=ev.clientX+14, y=ev.clientY-h/2;
    x=Math.min(Math.max(x,8),innerWidth-w-8);
    y=Math.min(Math.max(y,8),innerHeight-h-8);
    pop.style.left=x+"px"; pop.style.top=y+"px";
    pop.querySelector(".popup-x").onclick=closePopup;
  }
  addEventListener("keydown",e=>{if(e.key==="Escape")closePopup();});

  // ---- duplicate-coordinate spread (visual only; lat/lon unchanged) ------
  const GOLDEN=Math.PI*(3-Math.sqrt(5));
  const coordKey=p=>`${p.lat},${p.lon}`;

  function buildClusterLayout(all){
    const groups=new Map();
    all.forEach(r=>{
      const k=coordKey(r.p);
      if(!groups.has(k))groups.set(k,[]);
      groups.get(k).push(r);
    });
    const layout=new Map();
    groups.forEach(members=>{
      if(members.length<=1)return;
      members.sort((a,b)=>a.p.id-b.p.id);
      // rBase (NOT rOf) on purpose: cluster-spread positions must stay fixed
      // regardless of the marker-size slider, so it only changes size, never
      // where a marker sits.
      const maxR=Math.max(...members.map(m=>rBase(m.tax)));
      const baseSep=maxR*.55, step=maxR*.35, n=members.length;
      const raw=members.map((_,i)=>{
        const rad=baseSep+step*Math.sqrt(i), ang=i*GOLDEN;
        return[rad*Math.cos(ang),rad*Math.sin(ang)];});
      const cx=raw.reduce((s,o)=>s+o[0],0)/n, cy=raw.reduce((s,o)=>s+o[1],0)/n;
      members.forEach((m,i)=>layout.set(m.p.id,{dx:raw[i][0]-cx,dy:raw[i][1]-cy}));
    });
    return layout;
  }
  function visPos(r,layout){
    const bx=px(r.p.lon), by=py(r.p.lat);
    const off=layout.get(r.p.id);
    return off?{x:bx+off.dx,y:by+off.dy}:{x:bx,y:by};
  }
  function tipHtml(r,tier,year){
    return `<b>${r.p.name}</b>`+(r.p.modern?` <span class="m">= ${r.p.modern}</span>`:"")
      +`<br>${DATA.counties[r.p.cty].name} county · ${year}`
      +`<br>taxable <b>${fmt(r.tax)}</b> selišta`
      +(r.ab>0?` · abandoned ${fmt(r.ab)}`:"")
      +`<br><span class="m">${TIER[tier].label}</span>`;
  }

  // ---- MAP -------------------------------------------------------------
  const ringPath=r=>r.map((q,i)=>(i?"L":"M")+px(q[0]).toFixed(1)+" "
    +py(q[1]).toFixed(1)).join(" ")+"Z";
  const linePath=r=>r.map((q,i)=>(i?"L":"M")+px(q[0]).toFixed(1)+" "
    +py(q[1]).toFixed(1)).join(" ");
  function drawMap(year){
    if(typeof closePopup==="function")closePopup();
    const svg=mapSvg; svg.textContent="";
    // county borders (context), then rivers, then everything else on top
    (DATA.geo.counties||[]).forEach(c=>
      c.rings.forEach(r=>svg.appendChild(el("path",{d:ringPath(r),class:"border"}))));
    (DATA.geo.rivers||[]).forEach(rv=>rv.lines.forEach(l=>
      svg.appendChild(el("path",{d:linePath(l),class:"river"}))));
    // county towns
    for(const id in DATA.counties){
      if(hiddenCounties.has(+id))continue;
      const c=DATA.counties[id];
      const x=px(c.cap[1]),y=py(c.cap[0]);
      svg.appendChild(el("path",{class:"capdot",
        d:`M${x-4} ${y}H${x+4}M${x} ${y-4}V${y+4}`}));
      const t=el("text",{x:x+6,y:y-6,class:"cap"});t.textContent=c.name;
      svg.appendChild(t);}
    // markers go in their own <g> so a zoom can resize them (keeping their
    // on-screen size constant) without rebuilding the static borders/rivers.
    curYear=year;
    markersG=el("g",{}); svg.appendChild(markersG);
    drawMarkers();
  }
  // Markers keep a CONSTANT on-screen size at every zoom: the map (borders,
  // rivers, spacing) grows as you zoom, but a marker's radius is scaled by
  // vb.w/MW (= 1/zoom), which cancels the SVG's viewBox magnification, so each
  // marker stays exactly the pixel size it has when fully zoomed out.
  let curYear=null, markersG=null;
  function drawMarkers(){
    if(!markersG||curYear==null)return;
    markersG.textContent="";
    const sc=vb.w/MW;   // 1 at zoom-out, shrinks with zoom to hold screen size
    // fallback (red) cloud behind, then yellow, then confident green on top;
    // within a tier largest first so small ones stay clickable.
    const all=(DATA.burden[curYear]||[]).map(e=>({p:byId[e[0]],tax:e[1],ab:e[2]}))
      .filter(r=>r.p&&!hiddenCounties.has(r.p.cty));
    const layout=buildClusterLayout(all);
    const opac=[.82,.82,.5];
    [2,1,0].forEach(tier=>{
      all.filter(r=>r.p.tier===tier).sort((a,b)=>b.tax-a.tax).forEach(r=>{
        const v=visPos(r,layout);
        const c=marker(r.p.cty,v.x,v.y,rOf(r.tax)*sc,
          cssv("--"+TIER[tier].k),opac[tier]);
        c.addEventListener("pointerenter",ev=>showTip(tipHtml(r,tier,curYear),ev));
        c.addEventListener("pointermove",ev=>showTip(tip.innerHTML,ev));
        c.addEventListener("pointerleave",hideTip);
        c.addEventListener("click",ev=>{ev.stopPropagation();
          showPopup(r,tier,curYear,ev);});
        markersG.appendChild(c);});});
  }
  function mapLegend(){
    const tc=DATA.tierCounts;
    const shapes=[4,1,2,3].map(c=>
      `<span style="color:var(--ink2)">${SHAPEGLYPH[c]}</span>&nbsp;${DATA.counties[c].name}`)
      .join("&nbsp;&nbsp;");
    $("map-legend").innerHTML=
      `<span class="item"><span class="m">County:</span> ${shapes}</span>`
      +TIER.map((t,i)=>
        `<span class="item"><span class="dot" style="background:var(--${t.k})"></span>`
        +`${t.label} <span class="m">(${tc[i]})</span></span>`).join("")
      +`<span class="item"><span class="dot" style="width:8px;height:8px"></span>`
      +`<span class="dot" style="width:18px;height:18px"></span>`
      +`<span class="m">smaller → larger tax base</span></span>`;
  }

  // ---- controls --------------------------------------------------------
  function sync(){drawMap(cur());}
  const cur=()=>DATA.years[+$("slider").value];
  $("theme").onclick=()=>{const d=!isDark();
    document.documentElement.setAttribute("data-theme",d?"dark":"light");
    $("theme").textContent=d?"Light":"Dark";sync();};

  // ---- marker size slider (1x–2x) -----------------------------------------
  const msizeSlider=$("msize");
  if(msizeSlider)msizeSlider.oninput=()=>{
    msizeMult=+msizeSlider.value;
    if(typeof drawMarkers==="function")drawMarkers();   // radius reads msizeMult live
  };

  // ---- per-county visibility panel --------------------------------------
  const layerPanel=$("layer-panel");
  const countyOrder=[4,1,2,3].filter(id=>DATA.counties[id]);
  layerPanel.innerHTML=countyOrder.map(id=>
    `<label class="row"><input type="checkbox" data-id="${id}" checked>`
    +`${DATA.counties[id].name}</label>`
  ).join("");
  layerPanel.querySelectorAll("input[data-id]").forEach(b=>
    b.addEventListener("change",()=>{
      const id=+b.dataset.id;
      if(b.checked)hiddenCounties.delete(id);else hiddenCounties.add(id);
      sync();
    }));

  // slider + play
  const sl=$("slider"); sl.max=DATA.years.length-1;
  sl.value=DATA.years.indexOf(1507)>=0?DATA.years.indexOf(1507):0;
  // Year ticks under the track (clickable). Thumb inset ~7px each side.
  const yearMarks=[];
  const yearsBox=$("slider-years");
  const nYears=DATA.years.length;
  DATA.years.forEach((y,i)=>{
    const b=document.createElement("button");
    b.type="button"; b.textContent=y; b.title=String(y);
    b.style.left=nYears<=1?"50%":
      `calc(${i/(nYears-1)} * (100% - 14px) + 7px)`;
    b.onclick=()=>{sl.value=i;drawMap(cur());markYear();};
    yearsBox.appendChild(b); yearMarks.push(b);
  });
  function markYear(){
    const i=+$("slider").value;
    yearMarks.forEach((b,j)=>b.setAttribute("aria-current",j===i?"true":"false"));
  }
  const onSlide=()=>{drawMap(cur());markYear();};
  sl.oninput=onSlide;
  let timer=null;
  $("play").onclick=()=>{
    if(timer){clearInterval(timer);timer=null;$("play").textContent="▶";return;}
    $("play").textContent="⏸";sync();
    timer=setInterval(()=>{
      sl.value=(+sl.value+1)%DATA.years.length;onSlide();
      if(+sl.value===DATA.years.length-1){clearInterval(timer);timer=null;
        $("play").textContent="▶";}},900);};
  markYear();

  mapLegend(); sync();
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change",sync);
})();
