(function(){
  "use strict";
  if(typeof DATA==="undefined"||!DATA)return;

  const PAGE=100;
  const $=id=>document.getElementById(id);
  const LABELS={
    entry_id:"Entry", year:"Year", tax_type:"Tax type",
    county:"County", judge_name:"District", place:"Place (historical)",
    place_canonical:"Place (canonical)", modern_place:"Modern place",
    first_name:"First name", surname:"Surname",
    family_status_canonical:"Status", title_canonical:"Title",
    institution_canonical:"Institution", taxable_selista:"Taxable selišta",
    abandoned_selista:"Abandoned selišta", inferred:"Inferred"
  };
  const NUM=new Set(["entry_id","year","taxable_selista",
    "abandoned_selista","inferred"]);
  const COL=Object.fromEntries(DATA.cols.map((c,i)=>[c,i]));
  const fmt=n=>n==null?"":n;
  const fold=s=>(s||"").toLowerCase();

  let filtered=[], page=0, sortCol=COL.year, sortDesc=false;

  const isDark=()=>document.documentElement.getAttribute("data-theme")==="dark"
      ||(!document.documentElement.getAttribute("data-theme")
        &&matchMedia("(prefers-color-scheme: dark)").matches);

  // ---- filter UI -------------------------------------------------------
  const yearSel=$("f-year");
  DATA.years.forEach(y=>{
    const o=document.createElement("option");
    o.value=y; o.textContent=y; o.selected=true; yearSel.appendChild(o);
  });

  function addChecks(container, values, prefix){
    values.forEach(v=>{
      const id=prefix+"-"+v.replace(/\W+/g,"");
      const lab=document.createElement("label");
      const cb=document.createElement("input");
      cb.type="checkbox"; cb.value=v; cb.id=id; cb.checked=true;
      cb.dataset.filter=prefix;
      lab.appendChild(cb);
      lab.appendChild(document.createTextNode(" "+v));
      container.appendChild(lab);
    });
  }
  addChecks($("f-county"), DATA.counties, "county");
  addChecks($("f-tax"), DATA.taxTypes, "tax");

  const headRow=$("head-row");
  DATA.cols.forEach(c=>{
    const th=document.createElement("th");
    th.textContent=LABELS[c]||c;
    th.dataset.col=c;
    if(NUM.has(c))th.classList.add("num");
    if(c===DATA.cols[sortCol])th.classList.add("sorted");
    th.addEventListener("click",()=>{
      if(sortCol===COL[c])sortDesc=!sortDesc;
      else{sortCol=COL[c];sortDesc=NUM.has(c);}
      apply();
    });
    headRow.appendChild(th);
  });

  function selectedYears(){
    return new Set([...yearSel.selectedOptions].map(o=>+o.value));
  }
  function checkedValues(prefix){
    return new Set([...document.querySelectorAll(
      `input[data-filter="${prefix}"]:checked`)].map(el=>el.value));
  }

  function matchFilters(row){
    const yrs=selectedYears();
    if(yrs.size&&row[COL.year]!=null&&!yrs.has(row[COL.year]))return false;
    const counties=checkedValues("county");
    if(!counties.size)return false;
    if(row[COL.county]&&!counties.has(row[COL.county]))return false;
    const taxes=checkedValues("tax");
    if(!taxes.size)return false;
    if(row[COL.tax_type]&&!taxes.has(row[COL.tax_type]))return false;

    const place=fold($("f-place").value.trim());
    if(place){
      const hay=fold(row[COL.place])+" "+fold(row[COL.place_canonical])
        +" "+fold(row[COL.modern_place]);
      if(!hay.includes(place))return false;
    }
    const person=fold($("f-person").value.trim());
    if(person){
      const hay=fold(row[COL.first_name])+" "+fold(row[COL.surname]);
      if(!hay.includes(person))return false;
    }
    const inst=fold($("f-institution").value.trim());
    if(inst&&!fold(row[COL.institution_canonical]).includes(inst))return false;
    const tmin=$("f-tax-min").value, tmax=$("f-tax-max").value;
    const tax=row[COL.taxable_selista];
    if(tmin!==""&&(tax==null||tax<+tmin))return false;
    if(tmax!==""&&(tax==null||tax>+tmax))return false;
    return true;
  }

  function cmp(a,b){
    const av=a[sortCol], bv=b[sortCol];
    if(av==null&&bv==null)return 0;
    if(av==null)return 1;
    if(bv==null)return -1;
    let c;
    if(typeof av==="number"&&typeof bv==="number")c=av-bv;
    else c=String(av).localeCompare(String(bv),undefined,{numeric:true});
    return sortDesc?-c:c;
  }

  function apply(){
    filtered=DATA.rows.filter(matchFilters);
    filtered.sort(cmp);
    page=0;
    render();
  }

  function render(){
    const pages=Math.max(1,Math.ceil(filtered.length/PAGE));
    if(page>=pages)page=pages-1;
    const start=page*PAGE, end=Math.min(start+PAGE,filtered.length);
    const body=$("tbl-body");
    body.textContent="";
    const frag=document.createDocumentFragment();
    for(let i=start;i<end;i++){
      const row=filtered[i], tr=document.createElement("tr");
      DATA.cols.forEach(c=>{
        const td=document.createElement("td");
        let v=row[COL[c]];
        if(c==="inferred")v=v?"*":"";
        else if(c==="taxable_selista"||c==="abandoned_selista")
          v=v==null?"":Math.round(v*10)/10;
        td.textContent=fmt(v);
        td.title=td.textContent;
        if(NUM.has(c))td.classList.add("num");
        tr.appendChild(td);
      });
      frag.appendChild(tr);
    }
    body.appendChild(frag);

    $("stat").textContent=filtered.length
      ?`Showing ${(start+1).toLocaleString("en")}–${end.toLocaleString("en")}`
        +` of ${filtered.length.toLocaleString("en")} matching rows`
      :"No matching rows";
    $("pg-lab").textContent=`Page ${page+1} / ${pages}`;
    $("pg-first").disabled=page===0;
    $("pg-prev").disabled=page===0;
    $("pg-next").disabled=page>=pages-1;
    $("pg-last").disabled=page>=pages-1;

    headRow.querySelectorAll("th").forEach(th=>{
      th.classList.toggle("sorted",COL[th.dataset.col]===sortCol);
      th.classList.toggle("desc",COL[th.dataset.col]===sortCol&&sortDesc);
    });
  }

  function exportCsv(){
    const esc=v=>{
      const s=v==null?"":String(v);
      return /[",\n]/.test(s)?'"'+s.replace(/"/g,'""')+'"':s;
    };
    const header=DATA.cols.map(c=>LABELS[c]||c);
    const lines=[header.map(esc).join(",")];
    filtered.forEach(row=>{
      lines.push(DATA.cols.map(c=>{
        let v=row[COL[c]];
        if(c==="inferred")v=v?1:0;
        return esc(v);
      }).join(","));
    });
    const blob=new Blob([lines.join("\n")],{type:"text/csv;charset=utf-8"});
    const a=document.createElement("a");
    a.href=URL.createObjectURL(blob);
    a.download="tax_entries_filtered.csv";
    a.click();
    URL.revokeObjectURL(a.href);
  }

  function resetFilters(){
    $("f-place").value=""; $("f-person").value="";
    $("f-institution").value="";
    $("f-tax-min").value=""; $("f-tax-max").value="";
    [...yearSel.options].forEach(o=>o.selected=true);
    document.querySelectorAll("input[data-filter]").forEach(cb=>cb.checked=true);
    apply();
  }

  let debounce=null;
  function scheduleApply(){
    clearTimeout(debounce);
    debounce=setTimeout(apply,180);
  }

  $("filters").addEventListener("input",ev=>{
    if(ev.target.id==="f-place"||ev.target.id==="f-person"
        ||ev.target.id==="f-institution"
        ||ev.target.id==="f-tax-min"||ev.target.id==="f-tax-max")
      scheduleApply();
    else apply();
  });
  $("filters").addEventListener("change",apply);
  $("pg-first").onclick=()=>{page=0;render();};
  $("pg-prev").onclick=()=>{page--;render();};
  $("pg-next").onclick=()=>{page++;render();};
  $("pg-last").onclick=()=>{page=Math.ceil(filtered.length/PAGE)-1;render();};
  $("export").onclick=exportCsv;
  $("reset").onclick=resetFilters;

  $("theme").onclick=()=>{
    const d=!isDark();
    document.documentElement.setAttribute("data-theme",d?"dark":"light");
    $("theme").textContent=d?"Light":"Dark";
  };
  $("theme").textContent=isDark()?"Light":"Dark";

  apply();
})();
