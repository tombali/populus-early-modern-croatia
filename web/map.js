(function(){
  "use strict";
  if(typeof DATA==="undefined"||!DATA)return;
  const $=id=>document.getElementById(id);
  const tip=$("tip");
  const TIER=[{k:"good",label:"Exact location"},
              {k:"warn",label:"Approximate (uncertain / fuzzy)"},
              {k:"crit",label:"No coordinates → near county town"}];
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
  // frame the map by the county borders too, so the region is fully shown
  (DATA.geo.counties||[]).forEach(c=>c.rings.forEach(r=>r.forEach(q=>grow(q[0],q[1]))));
  const pad=.05*(latMax-latMin);
  latMin-=pad;latMax+=pad;lonMin-=pad;lonMax+=pad;
  const midLat=(latMin+latMax)/2, kx=Math.cos(midLat*Math.PI/180);
  const geoW=(lonMax-lonMin)*kx, geoH=(latMax-latMin);
  const MW=1000, MH=Math.round(MW*geoH/geoW);
  const mapSvg=$("map");
  mapSvg.setAttribute("viewBox",`0 0 ${MW} ${MH}`);
  const px=lon=>((lon-lonMin)*kx)/geoW*MW;
  const py=lat=>(latMax-lat)/geoH*MH;

  // ---- pan / zoom (viewBox) --------------------------------------------
  const vb0={x:0,y:0,w:MW,h:MH};
  let vb={...vb0};
  const MIN_Z=1, MAX_Z=32;
  function applyVB(){
    mapSvg.setAttribute("viewBox",`${vb.x} ${vb.y} ${vb.w} ${vb.h}`);}
  function zoomAt(factor,cx,cy){
    const nx=vb.x+cx*vb.w, ny=vb.y+cy*vb.h;
    const nw=Math.min(Math.max(vb.w/factor,vb0.w/MAX_Z),vb0.w/MIN_Z);
    const nh=nw*vb0.h/vb0.w;
    vb.x=nx-cx*nw; vb.y=ny-cy*nh; vb.w=nw; vb.h=nh; applyVB();}
  function resetView(){vb={...vb0};applyVB();}
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

  // ---- map size scale --------------------------------------------------
  let maxTax=1;
  Object.values(DATA.burden).forEach(a=>a.forEach(e=>maxTax=Math.max(maxTax,e[1])));
  const rOf=t=>t<=0?1.6:1.8+16*Math.sqrt(t)/Math.sqrt(maxTax);

  const SVGNS="http://www.w3.org/2000/svg";
  const el=(n,a)=>{const e=document.createElementNS(SVGNS,n);
    for(const k in a)e.setAttribute(k,a[k]);return e;};

  // shape encodes county (colour is reserved for confidence tier)
  const SHAPE={4:"circle",1:"square",2:"triangle",3:"diamond"};
  const SHAPEGLYPH={4:"●",1:"■",2:"▲",3:"◆"};
  function marker(cty,x,y,r,fill,op){
    const a={fill,"fill-opacity":op,stroke:cssv("--surface"),"stroke-width":.7};
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
      const maxR=Math.max(...members.map(m=>rOf(m.tax)));
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
    const svg=mapSvg; svg.textContent="";
    // county borders (context), then rivers, then everything else on top
    (DATA.geo.counties||[]).forEach(c=>c.rings.forEach(r=>
      svg.appendChild(el("path",{d:ringPath(r),class:"border"}))));
    (DATA.geo.rivers||[]).forEach(rv=>rv.lines.forEach(l=>
      svg.appendChild(el("path",{d:linePath(l),class:"river"}))));
    // county towns
    for(const id in DATA.counties){const c=DATA.counties[id];
      const x=px(c.cap[1]),y=py(c.cap[0]);
      svg.appendChild(el("path",{class:"capdot",
        d:`M${x-4} ${y}H${x+4}M${x} ${y-4}V${y+4}`}));
      const t=el("text",{x:x+6,y:y-6,class:"cap"});t.textContent=c.name;
      svg.appendChild(t);}
    // markers: fallback (red) cloud behind, then yellow, then confident green
    // on top; within a tier largest first so small ones stay clickable.
    const all=(DATA.burden[year]||[]).map(e=>({p:byId[e[0]],tax:e[1],ab:e[2]}))
      .filter(r=>r.p);
    const layout=buildClusterLayout(all);
    const opac=[.82,.82,.5];
    [2,1,0].forEach(tier=>{
      all.filter(r=>r.p.tier===tier).sort((a,b)=>b.tax-a.tax).forEach(r=>{
        const v=visPos(r,layout);
        const c=marker(r.p.cty,v.x,v.y,rOf(r.tax),
          cssv("--"+TIER[tier].k),opac[tier]);
        c.addEventListener("pointerenter",ev=>showTip(tipHtml(r,tier,year),ev));
        c.addEventListener("pointermove",ev=>showTip(tip.innerHTML,ev));
        c.addEventListener("pointerleave",hideTip);
        svg.appendChild(c);});});
    $("yrlab").textContent=year;
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

  // ---- TABLE (accessibility) ------------------------------------------
  const order=[4,1,2,3];
  function drawTable(){
    let h=`<table><caption>Taxable selišta by county and census year</caption>`
      +`<thead><tr><th>Year</th>`
      +order.map(c=>`<th>${DATA.counties[c].name}</th>`).join("")+`</tr></thead><tbody>`;
    DATA.years.forEach(y=>{h+=`<tr><td>${y}</td>`+order.map(c=>{
      const d=(DATA.trends[c]||[]).find(p=>p[0]===y);
      return `<td>${d?fmt(d[1]):"·"}</td>`;}).join("")+`</tr>`;});
    $("panel-table").innerHTML=h+`</tbody></table>`;
  }

  // ---- controls --------------------------------------------------------
  let tableOn=false;
  function sync(){
    $("panel-map").classList.toggle("hidden",tableOn);
    $("panel-table").classList.toggle("hidden",!tableOn);
    $("tbl").setAttribute("aria-pressed",tableOn);
    if(tableOn)drawTable();
    else drawMap(cur());
  }
  const cur=()=>DATA.years[+$("slider").value];
  $("tbl").onclick=()=>{tableOn=!tableOn;sync();};
  $("theme").onclick=()=>{const d=!isDark();
    document.documentElement.setAttribute("data-theme",d?"dark":"light");
    $("theme").textContent=d?"Light":"Dark";sync();};

  // slider + play
  const sl=$("slider"); sl.max=DATA.years.length-1;
  sl.value=DATA.years.indexOf(1507)>=0?DATA.years.indexOf(1507):0;
  sl.oninput=()=>{if(!tableOn)drawMap(cur());};
  let timer=null;
  $("play").onclick=()=>{
    if(timer){clearInterval(timer);timer=null;$("play").textContent="▶";return;}
    $("play").textContent="⏸";sync();
    timer=setInterval(()=>{
      sl.value=(+sl.value+1)%DATA.years.length;drawMap(cur());
      if(+sl.value===DATA.years.length-1){clearInterval(timer);timer=null;
        $("play").textContent="▶";}},900);};

  mapLegend(); sync();
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change",sync);
})();
