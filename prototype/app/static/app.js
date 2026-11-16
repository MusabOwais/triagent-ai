"use strict";
const $ = (s, el = document) => el.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const app = $("#app");
let META = null, timer = null;

async function api(path, opts = {}) {
  const r = await fetch(path, {headers: opts.body instanceof FormData ? {} : {"Content-Type": "application/json"}, ...opts});
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(j.detail ? (typeof j.detail === "string" ? j.detail : "Check the highlighted fields: some values are out of range.") : "Request failed.");
  return j;
}
function toast(msg) { const t = $("#toast"); t.textContent = msg; t.hidden = false; clearTimeout(toast.h); toast.h = setTimeout(() => t.hidden = true, 3200); }

const band = s => s >= 80 ? ["Critical","crit"] : s >= 60 ? ["High","high"] : s >= 40 ? ["Moderate","mod"] : s >= 20 ? ["Low","low"] : ["Minimal","min"];
const pill = s => `<span class="s b-${band(s)[1]}">${s}</span>`;
const fmtMin = m => m == null ? "" : m < 60 ? `${Math.round(m)} min` : `${Math.floor(m/60)} h ${Math.round(m%60)} min`;
const sgn = x => (x >= 0 ? "+" : "−") + Math.abs(x).toFixed(2);
const shortName = n => esc(String(n).replace(/^Example patient:\s*/, ""));

// ---------------- router ----------------
async function route() {
  clearInterval(timer);
  const h = location.hash.slice(1) || "board";
  document.querySelectorAll("nav a").forEach(a => a.classList.toggle("on", a.dataset.view === h));
  if (!META) META = await api("/api/meta");
  if (h === "ambulance") return renderIntake();
  if (h.startsWith("p-")) return renderPatient(h.slice(2));
  renderBoard(); timer = setInterval(renderBoard, 5000);
}
addEventListener("hashchange", route);
$("#reset").onclick = async () => { await api("/api/reset", {method: "POST"}); toast("Demo reset to the example patients."); route(); };

// ---------------- ambulance intake ----------------
const DEFAULTS = {name:"", age:58, sex:"M", dob:"", complaint:"cc_chestpain", complaint_detail:"", onset:"", mechanism:"",
  history:"", medications:"", allergies:"", treatments:"", hr:96, sbp:138, dbp:84, rr:18, spo2:96, temp_f:98.6, o2:false,
  gcs:15, pain:5, rhythm:"sinus", injuries:[], order_ecg:true, order_xray:true};

function renderIntake() {
  const d = DEFAULTS;
  const opt = (v, l, sel) => `<option value="${esc(v)}"${sel ? " selected" : ""}>${esc(l)}</option>`;
  app.innerHTML = `
  <h1>Ambulance intake</h1>
  <p class="sub">Enter what the crew measures. The score updates as you type. Sending creates the handoff and a provisional bed request at the ER.</p>
  <form id="f" class="intake" novalidate>
    <div class="stack">
      <section class="panel stack"><h2>Patient</h2>
        <div class="grid">
          <label>Name<input id="name" name="name" placeholder="Full name"></label>
          <label>Age<input id="age" name="age" type="number" min="18" max="110" value="${d.age}"></label>
          <label>Sex<select id="sex" name="sex">${opt("M","Male",d.sex==="M")}${opt("F","Female",d.sex==="F")}</select></label>
          <label>Date of birth<input id="dob" name="dob" type="date"></label>
        </div></section>
      <section class="panel stack"><h2>Chief complaint</h2>
        <div class="grid wide">
          <label>Main reason for the call<select id="complaint" name="complaint">
            ${META.complaints.map(c => opt(c.id, c.label, c.id === d.complaint)).join("")}
            ${opt("", "Other, not listed (Model B, no complaint weight)")}
            ${opt("__none", "Unknown, patient cannot say (uses Model A)")}
          </select></label>
          <label>Symptom details<input id="complaint_detail" name="complaint_detail" placeholder="What the patient describes"></label>
          <label>Time of onset<input id="onset" name="onset" placeholder="e.g. 30 min before call"></label>
          <label>For injuries: how and when it happened<input id="mechanism" name="mechanism" placeholder="Mechanism and time"></label>
        </div></section>
      <section class="panel stack"><h2>Vital signs</h2>
        <div class="grid">
          <label>Heart rate <span class="unit">bpm</span><input id="hr" name="hr" type="number" value="${d.hr}"></label>
          <label>Systolic BP <span class="unit">mmHg</span><input id="sbp" name="sbp" type="number" value="${d.sbp}"></label>
          <label>Diastolic BP <span class="unit">mmHg</span><input id="dbp" name="dbp" type="number" value="${d.dbp}"></label>
          <label>Breathing rate <span class="unit">/min</span><input id="rr" name="rr" type="number" value="${d.rr}"></label>
          <label>SpO2 <span class="unit">%</span><input id="spo2" name="spo2" type="number" value="${d.spo2}"></label>
          <label>Temperature <span class="unit">°F</span><input id="temp_f" name="temp_f" type="number" step="0.1" value="${d.temp_f}"></label>
          <label>GCS <span class="unit">3–15</span><input id="gcs" name="gcs" type="number" min="3" max="15" value="${d.gcs}"></label>
          <label>Pain <span class="unit">0–10</span><input id="pain" name="pain" type="number" min="0" max="10" value="${d.pain}"></label>
          <label>Cardiac rhythm<select id="rhythm" name="rhythm">${META.rhythms.map(r => opt(r.id, r.label, r.id === d.rhythm)).join("")}</select></label>
        </div>
        <label class="chk" style="align-self:flex-start"><input id="o2" name="o2" type="checkbox"> On supplemental oxygen</label></section>
      <section class="panel stack"><h2>Visible injuries</h2>
        <div class="checks">${META.injuries.map(i => `<label class="chk"><input type="checkbox" name="injuries" value="${i}" id="inj-${i}"> ${esc(i.replace(/_/g," "))}</label>`).join("")}</div></section>
      <section class="panel stack"><h2>Medical information</h2>
        <div class="grid wide">
          <label>Relevant history<textarea id="history" name="history"></textarea></label>
          <label>Current medications<textarea id="medications" name="medications"></textarea></label>
          <label>Allergies<textarea id="allergies" name="allergies"></textarea></label>
          <label>Treatments given (time, dose, IV fluids)<textarea id="treatments" name="treatments"></textarea></label>
        </div></section>
      <section class="panel stack"><h2>Diagnostics to queue on arrival</h2>
        <div class="checks"><label class="chk"><input id="order_ecg" name="order_ecg" type="checkbox" checked> 12-lead ECG</label>
        <label class="chk"><input id="order_xray" name="order_xray" type="checkbox" checked> Chest X-ray</label></div></section>
    </div>
    <aside class="panel stack live" id="live"><p class="muted">Calculating…</p></aside>
  </form>`;
  const f = $("#f");
  f.addEventListener("input", () => { clearTimeout(f.h); f.h = setTimeout(preview, 200); });
  preview();
}

function readForm() {
  const f = $("#f"), g = id => f.querySelector("#" + id);
  const c = g("complaint").value;
  return {name: g("name").value.trim(), age: +g("age").value, sex: g("sex").value, dob: g("dob").value,
    complaint: c === "__none" ? null : c, complaint_detail: g("complaint_detail").value, onset: g("onset").value,
    mechanism: g("mechanism").value, history: g("history").value, medications: g("medications").value,
    allergies: g("allergies").value, treatments: g("treatments").value,
    hr: +g("hr").value, sbp: +g("sbp").value, dbp: +g("dbp").value, rr: +g("rr").value, spo2: +g("spo2").value,
    temp_f: +g("temp_f").value, o2: g("o2").checked, gcs: +g("gcs").value, pain: +g("pain").value, rhythm: g("rhythm").value,
    injuries: [...f.querySelectorAll("input[name=injuries]:checked")].map(x => x.value),
    order_ecg: g("order_ecg").checked, order_xray: g("order_xray").checked};
}

function contribRows(parts) {
  return parts.filter(p => p[0] !== "Intercept").map(([k, v]) => {
    const w = Math.min(Math.abs(v) / 2.5, 1) * 50;
    return `<div><span>${esc(k)}</span><span class="num">${sgn(v)}</span><span class="bar"><i class="${v >= 0 ? "pos" : "neg"}" style="width:${w}%"></i></span></div>`;
  }).join("") || `<p class="muted small">All inputs in the normal range.</p>`;
}

async function preview() {
  const live = $("#live"); if (!live) return;
  let r;
  try { r = await api("/api/preview", {method: "POST", body: JSON.stringify(readForm())}); }
  catch (e) { live.innerHTML = `<h3>Risk score</h3><p>${esc(e.message)} Age must be 18–110, GCS 3–15 and pain 0–10.</p>`; return; }
  const [bl, bc] = band(r.score);
  live.innerHTML = `
    <h3>Ambulance risk score</h3>
    <div class="gauge"><span class="big">${r.score}</span><span class="band b-${bc}">${bl}</span></div>
    <div class="scale">${"<span></span>".repeat(5)}<i class="pin" style="left:calc(${r.score}% - 2px)"></i></div>
    <div class="scale-l"><span>1</span><span>20</span><span>40</span><span>60</span><span>80</span><span>100</span></div>
    <dl class="kv">
      <dt>Model</dt><dd>${r.model === "B" ? "Model B (vitals + complaint)" : "Model A (vitals only)"}</dd>
      <dt>Admission risk</dt><dd class="num">${Math.round(r.p_admit_model * 100)}% <span class="muted small">model only, calibrated on Yale</span></dd>
      <dt>NEWS2</dt><dd class="num">${r.news2} ${r.floor ? `<span class="chip ovr">floor ${r.floor}</span>` : ""}</dd>
      <dt>Provisional bed</dt><dd><b>${esc(r.bed)}</b> <span class="muted small">${esc(r.bed_reason)}</span></dd>
    </dl>
    ${r.floor > r.score_raw ? `<p class="small">Model and overlay give ${r.score_raw}. Raised to ${r.floor} because NEWS2 is ${r.news2}.</p>` : ""}
    <h3>What moved the score</h3>
    <div class="contrib">${contribRows(r.model_parts)}${r.overlay_parts.length ? `<div><span class="muted">EMT findings</span><span></span><span></span></div>` + contribRows(r.overlay_parts) : ""}</div>
    <button class="primary" id="send" type="button">Send handoff to ER</button>`;
  $("#send").onclick = async () => {
    const d = readForm();
    if (!d.name) { toast("Enter the patient's name before sending."); $("#name").focus(); return; }
    try { const p = await api("/api/patients", {method: "POST", body: JSON.stringify(d)});
      toast(`Handoff sent. ${d.name} is on the ER board as incoming.`); location.hash = "p-" + p.id; }
    catch (e) { toast(e.message); }
  };
}

// ---------------- ER board ----------------
function item(v, i, extra) {
  return `<button class="item" type="button" onclick="location.hash='p-${v.id}'">
    <span class="rank">${i + 1}</span>
    <span style="min-width:0"><span class="nm">${shortName(v.intake.name)}</span>
      <span class="meta">${extra}</span></span>
    ${pill(v.score)}</button>`;
}

async function renderBoard() {
  if (!location.hash.match(/^#?(board)?$/) && location.hash !== "#board") return;
  const b = await api("/api/board");
  const q = (svc, title) => `<section class="panel q"><div class="qh"><h2>${title}</h2><span class="muted small">${b[svc].length} waiting</span></div>
    ${b[svc].map((v, i) => item(v, i, `waiting ${fmtMin(v.queues[svc].minutes)} · priority <span class="num">${v.queues[svc].priority.toFixed(2)}</span>
      ${v.queues[svc].override ? ' <span class="chip ovr">10-min ECG rule</span>' : ""}`)).join("") || `<p class="empty">No one waiting.</p>`}</section>`;
  app.innerHTML = `
    <h1>ER board</h1>
    <p class="sub">Queues order by priority = log-odds + 0.01 × minutes waiting. Each bed type has its own waitlist; the score is the same on every list.</p>
    ${b.incoming.length ? `<h3 style="margin-bottom:8px">Incoming ambulances</h3><div class="incoming">${b.incoming.map(v =>
      `<div class="inc">${pill(v.score)}<a href="#p-${v.id}"><b>${shortName(v.intake.name)}</b></a>
       <span class="muted small">provisional ${esc(v.bed.type)}</span>
       <button class="btn" type="button" data-arrive="${v.id}">Mark arrived</button></div>`).join("")}</div>` : ""}
    <div class="board">${q("ecg", "ECG queue")}${q("xray", "Chest X-ray queue")}</div>
    <div class="beds">${META.beds.map(bed => `<section class="panel q"><div class="qh"><h2>${esc(bed)}</h2></div>
      ${b.beds[bed].map((v, i) => item(v, i, `<span class="chip ${v.bed.status === "confirmed" ? "conf" : ""}">${v.bed.status}</span> ${fmtMin(v.bed.minutes)}`)).join("") || `<p class="empty">Empty waitlist.</p>`}
      <button class="btn" type="button" data-assign="${esc(bed)}">Assign next ${esc(bed)} bed</button></section>`).join("")}</div>`;
  app.querySelectorAll("[data-arrive]").forEach(el => el.onclick = async () => { await api(`/api/patients/${el.dataset.arrive}/arrive`, {method: "POST"}); toast("Handoff received. Patient joined the diagnostic queues."); renderBoard(); });
  app.querySelectorAll("[data-assign]").forEach(el => el.onclick = async () => {
    try { const p = await api(`/api/beds/${encodeURIComponent(el.dataset.assign)}/assign`, {method: "POST"}); toast(`${el.dataset.assign} bed assigned to ${p.intake.name.replace(/^Example patient:\s*/, "")}.`); renderBoard(); }
    catch (e) { toast(e.message + " Confirm a patient's bed type on their page first."); } });
}

// ---------------- patient ----------------
async function renderPatient(id) {
  let p; try { p = await api(`/api/patients/${id}`); } catch (e) { app.innerHTML = `<p>${esc(e.message)} <a href="#board">Back to the ER board</a></p>`; return; }
  const I = p.intake, s1 = p.stage1, [bl, bc] = band(p.score);
  const row = (k, v) => v ? `<dt>${k}</dt><dd>${esc(v)}</dd>` : "";
  const rhythm = META.rhythms.find(r => r.id === I.rhythm)?.label;
  app.innerHTML = `
  <div class="row" style="justify-content:space-between;margin-bottom:14px">
    <div><h1>${shortName(I.name)}</h1><p class="sub" style="margin:0">${I.age} y · ${I.sex === "M" ? "male" : "female"} · ${esc(p.status)}${p.minutes_since_handoff != null ? ` · handed off ${fmtMin(p.minutes_since_handoff)} ago` : ""}</p></div>
    <div class="gauge"><span class="big" style="font-size:56px">${p.score}</span><span class="band b-${bc}">${bl}</span></div>
  </div>
  ${p.status === "incoming" ? `<div class="panel row" style="margin-bottom:16px;justify-content:space-between"><span>Ambulance en route. The ER can prepare a <b>${esc(p.bed.type)}</b> bed.</span><button class="primary" id="arrive" type="button">Mark arrived and receive handoff</button></div>` : ""}
  <div class="pt">
    <div class="stack">
      <section class="panel stack hand"><h2>Handoff record</h2>
        <div class="vit">
          <div><span>HR</span><b>${I.hr}</b></div><div><span>BP</span><b>${I.sbp}/${I.dbp}</b></div><div><span>RR</span><b>${I.rr}</b></div>
          <div><span>SpO2</span><b>${I.spo2}%</b></div><div><span>Temp °F</span><b>${I.temp_f}</b></div><div><span>GCS</span><b>${I.gcs}</b></div>
          <div><span>Pain</span><b>${I.pain}/10</b></div><div><span>O2</span><b>${I.o2 ? "Yes" : "No"}</b></div></div>
        <dl>
          ${row("Chief complaint", I.complaint == null ? "Unknown" : (META.complaints.find(c => c.id === I.complaint)?.label || "Other"))}
          ${row("Details", I.complaint_detail)}${row("Onset", I.onset)}${row("Mechanism", I.mechanism)}
          ${row("Cardiac rhythm", rhythm)}${row("Injuries", I.injuries.map(x => x.replace(/_/g, " ")).join(", "))}
          ${row("History", I.history)}${row("Medications", I.medications)}
          <dt>Allergies</dt><dd><b>${esc(I.allergies || "Not recorded")}</b></dd>
          ${row("Treatments given", I.treatments)}${row("Date of birth", I.dob)}
        </dl></section>
      <section class="panel stack"><h2>Score history</h2>
        <div class="tl">${p.events.map(e => `<div class="ev"><div>${esc(e.text)}</div><div class="when">${new Date(e.t * 1000).toLocaleTimeString([], {hour:"2-digit", minute:"2-digit"})} · score ${e.score}${e.dL ? ` · ${sgn(e.dL)} log-odds` : ""}</div></div>`).join("")}</div></section>
      <section class="panel stack"><h2>Ambulance score breakdown</h2>
        <dl class="kv"><dt>Model</dt><dd>${s1.model === "B" ? "Model B (vitals + complaint)" : "Model A (vitals only)"}</dd>
          <dt>NEWS2</dt><dd class="num">${s1.news2} (floor ${s1.floor})</dd><dt>Score</dt><dd class="num">${s1.score_raw} → ${s1.score}</dd></dl>
        <div class="contrib">${contribRows(s1.model_parts)}${contribRows(s1.overlay_parts)}</div></section>
    </div>
    <div class="stack">
      <section class="panel stack"><div class="qh"><h2>Bed</h2><span class="chip ${p.bed.status === "confirmed" ? "conf" : ""}">${esc(p.bed.status)}</span></div>
        <p style="margin:0"><b>${esc(p.bed.type)}</b> <span class="muted small">${esc(p.bed.reason)}</span></p>
        ${p.bed.status !== "assigned" && p.status !== "incoming" ? `<div class="row"><select id="bedsel">${META.beds.map(b => `<option${b === p.bed.type ? " selected" : ""}>${esc(b)}</option>`).join("")}</select>
          <button class="btn" id="confirm" type="button">Confirm bed type</button></div>
          <p class="muted small" style="margin:0">On the ${esc(p.bed.type)} waitlist for ${fmtMin(p.bed.minutes)} · priority <span class="num">${p.bed.priority.toFixed(2)}</span></p>` : ""}</section>
      ${diagPanel(p, "ecg")}
      ${diagPanel(p, "xray")}
    </div>
  </div>`;
  if ($("#arrive")) $("#arrive").onclick = async () => { await api(`/api/patients/${id}/arrive`, {method: "POST"}); toast("Handoff received."); renderPatient(id); };
  if ($("#confirm")) $("#confirm").onclick = async () => { await api(`/api/patients/${id}/bed/confirm`, {method: "POST", body: JSON.stringify({type: $("#bedsel").value})}); toast("Bed type confirmed."); renderPatient(id); };
  wireDiag(p);
}

function probRows(probs, kind) {
  const hotk = kind === "ecg" ? ["MI", "STTC", "CD"] : ["Pneumothorax", "Edema", "Pneumonia", "Consolidation", "Effusion"];
  const label = {NORM: "Normal", MI: "Myocardial infarction", STTC: "ST/T change", CD: "Conduction disturbance", HYP: "Hypertrophy", Pleural_Thickening: "Pleural thickening"};
  return Object.entries(probs).sort((a, b) => b[1] - a[1]).slice(0, kind === "ecg" ? 5 : 7).map(([k, v]) =>
    `<div><span>${esc(label[k] || k)}</span><span class="pbar"><i class="${hotk.includes(k) && v >= .5 ? "hot" : ""}" style="width:${(v * 100).toFixed(0)}%"></i></span><span class="num">${(v * 100).toFixed(0)}%</span></div>`).join("");
}

function diagPanel(p, kind) {
  const res = p[kind], name = kind === "ecg" ? "12-lead ECG" : "Chest X-ray", m = META.metrics;
  const note = kind === "ecg" ? `Model trained on PTB-XL · test AUROC ${m.ecg_auroc}` : `Model trained on NIH ChestX-ray14 · test AUROC ${m.cxr_auroc} · may only raise scores`;
  if (p.status === "incoming") return `<section class="panel stack"><h2>${name}</h2><p class="muted small">Available after the patient arrives.</p></section>`;
  if (res) {
    const truth = (META.samples[kind === "ecg" ? "ecg" : "cxr"].find(s => s.id === res.source) || {}).true_labels;
    return `<section class="panel stack"><div class="qh"><h2>${name}</h2><span class="num">${sgn(res.delta)} log-odds</span></div>
      <p class="muted small" style="margin:0">${note}</p>
      ${kind === "ecg" ? `<canvas class="ecg" id="trace"></canvas>` : (res.source.startsWith("upload") ? "" : `<img alt="Chest X-ray" style="max-width:220px;border-radius:6px" src="/samples/cxr/${esc((META.samples.cxr.find(s => s.id === res.source) || {}).file)}">`)}
      <div class="probs">${probRows(res.probs, kind)}</div>
      ${res.note ? `<p class="small" style="margin:0">${esc(res.note)}</p>` : ""}
      ${truth ? `<div class="truth">Demo transparency: the expert label for this held-out sample is <b>${esc(truth.join(", "))}</b>. The model has not seen it.</div>` : ""}</section>`;
  }
  const ordered = p.queues[kind];
  const samples = META.samples[kind === "ecg" ? "ecg" : "cxr"];
  const pick = kind === "ecg"
    ? `<label>Choose a held-out PTB-XL ECG<select id="ecgsel">${samples.map((s, i) => `<option value="${s.id}">ECG sample ${i + 1} · record ${s.ecg_id} · ${s.age} y ${s.sex}</option>`).join("")}</select></label>
       <canvas class="ecg" id="trace"></canvas>`
    : `<p class="small muted" style="margin:0">Choose a held-out NIH X-ray or upload your own image.</p>
       <div class="thumbs">${samples.map((s, i) => `<button type="button" data-cxr="${s.id}" class="${i ? "" : "sel"}" aria-label="X-ray sample ${i + 1}"><img alt="" src="/samples/cxr/${esc(s.file)}"></button>`).join("")}</div>
       <label>Or upload a chest X-ray (PNG or JPG)<input type="file" id="cxrfile" accept="image/*"></label>`;
  return `<section class="panel stack"><div class="qh"><h2>${name}</h2>${ordered ? `<span class="chip">in queue ${fmtMin(ordered.minutes)}</span>` : `<span class="chip">not ordered</span>`}</div>
    <p class="muted small" style="margin:0">${note}</p>${pick}
    <button class="primary" type="button" id="run-${kind}">Run ${kind === "ecg" ? "ECG" : "X-ray"} model and re-score</button></section>`;
}

async function drawEcg(sid) {
  const c = $("#trace"); if (!c || !sid) return;
  const d = await api(`/api/samples/ecg/${sid}`), lead = d.data[1];  // lead II
  const dpr = devicePixelRatio || 1, W = c.clientWidth, H = c.clientHeight;
  c.width = W * dpr; c.height = H * dpr; const g = c.getContext("2d"); g.scale(dpr, dpr);
  const cs = getComputedStyle(document.documentElement);
  g.strokeStyle = cs.getPropertyValue("--line"); g.lineWidth = 1;
  for (let x = 0; x < W; x += W / 50) { g.beginPath(); g.moveTo(x, 0); g.lineTo(x, H); g.stroke(); }
  const lo = Math.min(...lead), hi = Math.max(...lead), pad = 12;
  g.strokeStyle = cs.getPropertyValue("--crit"); g.lineWidth = 1.5; g.beginPath();
  lead.forEach((v, i) => { const x = i / (lead.length - 1) * W, y = H - pad - (v - lo) / (hi - lo || 1) * (H - 2 * pad); i ? g.lineTo(x, y) : g.moveTo(x, y); });
  g.stroke(); g.fillStyle = cs.getPropertyValue("--muted"); g.font = "12px IBM Plex Mono, monospace"; g.fillText("Lead II · 10 s", 8, 16);
}

function wireDiag(p) {
  const id = p.id;
  if (p.ecg) drawEcg(p.ecg.source);
  const es = $("#ecgsel"); if (es) { drawEcg(es.value); es.onchange = () => drawEcg(es.value); }
  const re = $("#run-ecg"); if (re) re.onclick = async () => {
    re.disabled = true; try { await api(`/api/patients/${id}/ecg`, {method: "POST", body: JSON.stringify({sample_id: es.value})}); toast("ECG read. Score updated."); renderPatient(id); }
    catch (e) { toast(e.message); re.disabled = false; } };
  let sel = META.samples.cxr[0]?.id;
  app.querySelectorAll("[data-cxr]").forEach(b => b.onclick = () => { sel = b.dataset.cxr; app.querySelectorAll("[data-cxr]").forEach(x => x.classList.toggle("sel", x === b)); });
  const rx = $("#run-xray"); if (rx) rx.onclick = async () => {
    rx.disabled = true;
    try {
      const f = $("#cxrfile").files[0];
      if (f) { const fd = new FormData(); fd.append("file", f); await api(`/api/patients/${id}/xray-upload`, {method: "POST", body: fd}); }
      else await api(`/api/patients/${id}/xray`, {method: "POST", body: JSON.stringify({sample_id: sel})});
      toast("X-ray read. Score updated."); renderPatient(id);
    } catch (e) { toast(e.message); rx.disabled = false; } };
}

route();
