import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { CSS2DRenderer, CSS2DObject } from 'three/addons/renderers/CSS2DRenderer.js';
import { Line2 } from 'three/addons/lines/Line2.js';
import { LineMaterial } from 'three/addons/lines/LineMaterial.js';
import { LineGeometry } from 'three/addons/lines/LineGeometry.js';

// ============================================================ estado
const E = {
  campos: null, pessoas: {}, med: {}, nome: '', coluna: null,
  proj: null, geo: null, foco: null, rotulos: {}, grupoDe: {}, job: null,
};
const OPCOES_PADRAO = { sexo: 'F', escala: 5, lado: 'D', com_braco: 'Sim', abducao: 15 };
const CORES_GRUPO = { contorno: 'var(--amarelo)', altura: 'var(--azul)', outras: 'var(--cinza-g)', extras: 'var(--verde)' };
const NOME_CONT = {
  busto: 'Busto', cintura: 'Cintura', peq_quadril: 'Pequeno quadril', quadril: 'Quadril', pescoco: 'Pescoço',
  gancho: 'Gancho', joelho: 'Joelho', braco: 'Braço', cotovelo: 'Cotovelo', pulso: 'Pulso', coxa: 'Coxa',
  panturrilha: 'Panturrilha', tornozelo: 'Tornozelo',
};
const PONTOS = [
  ['topo', 'Topo do pescoço'], ['c7', '7ª cervical'], ['ombro', 'Ponto do ombro'], ['jugular', 'Incisura jugular'],
  ['cava', 'Axila (cava)'], ['busto', 'Mamilo (busto)'], ['cintura', 'Cintura'], ['peq', 'Pequeno quadril'],
  ['quadril', 'Quadril'], ['gancho', 'Gancho'], ['coto', 'Corte da perna curta'], ['joelho', 'Joelho'],
  ['tornozelo', 'Fim da perna longa'],
];
const $ = (s) => document.querySelector(s);
const fmt = (v, c = 1) => (v === undefined || v === null || isNaN(v)) ? '—' : Number(v).toFixed(c).replace('.', ',');
const num = (s) => { if (s === '' || s === null || s === undefined) return null; const n = parseFloat(String(s).replace(',', '.')); return isNaN(n) ? null : n; };
function toast(t) { const el = $('#toast'); el.textContent = t; el.hidden = false; clearTimeout(toast.t); toast.t = setTimeout(() => el.hidden = true, 3200); }
function escMm() { return 10 / (num(E.med.escala) || 5); }

// ============================================================ 3D
const cena = $('#cena');
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
cena.appendChild(renderer.domElement);
const css = new CSS2DRenderer();
css.domElement.style.position = 'absolute'; css.domElement.style.inset = '0'; css.domElement.style.pointerEvents = 'none';
cena.appendChild(css.domElement);
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(28, 1, 1, 5000);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true; controls.dampingFactor = 0.08; controls.minDistance = 60; controls.maxDistance = 1200;
scene.add(new THREE.HemisphereLight(0xffffff, 0xd9d2c6, 1.15));
const sol = new THREE.DirectionalLight(0xffffff, 1.5); sol.position.set(-120, 260, -220); scene.add(sol);
const contra = new THREE.DirectionalLight(0xfff3e6, 0.55); contra.position.set(160, 120, 240); scene.add(contra);

const grupoCorpo = new THREE.Group(); scene.add(grupoCorpo);
const grupoBase = new THREE.Group(); scene.add(grupoBase);
const grupoCotas = new THREE.Group(); scene.add(grupoCotas);
const grade = new THREE.GridHelper(100, 20, 0xb9b2a6, 0xd8d2c8); scene.add(grade);
const matCorpo = new THREE.MeshStandardMaterial({ color: 0xe9d4bd, roughness: 0.72, metalness: 0, side: THREE.DoubleSide });
const matBraco = new THREE.MeshStandardMaterial({ color: 0xe2cbb1, roughness: 0.72, metalness: 0, side: THREE.DoubleSide });
const matBase = new THREE.MeshStandardMaterial({ color: 0x3b3936, roughness: 0.55, metalness: 0.2 });

// corpo (x, y=frente, z=altura) em cm  ->  three (x, z, -y)
const P = (p) => new THREE.Vector3(p[0], p[2], -p[1]);

function loftGeom(aneis, tampaIni = true, tampaFim = true) {
  const R = aneis.length, N = aneis[0].length;
  const pos = [], idx = [];
  for (const a of aneis) for (const p of a) pos.push(p[0], p[2], -p[1]);
  for (let i = 0; i < R - 1; i++) for (let j = 0; j < N; j++) {
    const a = i * N + j, b = i * N + (j + 1) % N, c = (i + 1) * N + (j + 1) % N, d = (i + 1) * N + j;
    idx.push(a, b, c, a, c, d);
  }
  const tampa = (anel, base, inv) => {
    let cx = 0, cy = 0, cz = 0; for (const p of anel) { cx += p[0]; cy += p[1]; cz += p[2]; }
    const k = pos.length / 3; pos.push(cx / N, cz / N, -cy / N);
    for (let j = 0; j < N; j++) inv ? idx.push(k, base + (j + 1) % N, base + j) : idx.push(k, base + j, base + (j + 1) % N);
  };
  if (tampaIni) tampa(aneis[0], 0, true);
  if (tampaFim) tampa(aneis[R - 1], (R - 1) * N, false);
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setIndex(idx); g.computeVertexNormals();
  return g;
}

function b64(s, Tipo) {
  const bin = atob(s); const u8 = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
  return new Tipo(u8.buffer);
}
function malhaGeom(m) {   // malha do campo de distância (mesmo corpo do arquivo final)
  const v = b64(m.v, Float32Array);
  const pos = new Float32Array(v.length);
  for (let i = 0; i < v.length; i += 3) { pos[i] = v[i]; pos[i + 1] = v[i + 2]; pos[i + 2] = -v[i + 1]; }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  g.setIndex(new THREE.BufferAttribute(b64(m.i, m.i16 ? Uint16Array : Uint32Array), 1));
  g.computeVertexNormals();
  return g;
}

function limpar(grupo) {
  for (const o of [...grupo.children]) {
    grupo.remove(o);
    o.traverse?.((c) => { c.geometry?.dispose(); if (c.material && c.material !== matCorpo && c.material !== matBraco && c.material !== matBase) c.material.dispose?.(); });
    if (o.isCSS2DObject) o.element.remove();
  }
}

function montarCorpo(geo) {
  limpar(grupoCorpo); limpar(grupoBase);
  grupoCorpo.add(new THREE.Mesh(malhaGeom(geo.malha), matCorpo));
  if (geo.braco && geo.braco.length > 2) grupoCorpo.add(new THREE.Mesh(loftGeom(geo.braco), matBraco));
  // base + haste
  const h = geo.haste;
  const espBase = 5 / escMm(), hBoss = 17 / escMm();
  const placa = new THREE.Mesh(new THREE.BoxGeometry(h.base, espBase, h.base), matBase);
  placa.position.set(h.x, espBase / 2, -h.y);
  const boss = new THREE.Mesh(new THREE.CylinderGeometry(h.d / 2 + 6 / escMm(), h.d / 2 + 6 / escMm(), hBoss, 40), matBase);
  boss.position.set(h.x, hBoss / 2, -h.y);
  const haste = new THREE.Mesh(new THREE.CylinderGeometry(h.d / 2, h.d / 2, h.topo - 0.6, 32), matBase);
  haste.position.set(h.x, (h.topo - 0.6) / 2 + 0.6, -h.y);
  grupoBase.add(placa, boss, haste);
  aplicarAlternar();
}

// ---- cotas
const matCotaFraca = () => new LineMaterial({ color: new THREE.Color(0x8f877b), linewidth: 1.2, transparent: true, opacity: 0.6, depthTest: true });
const matCotaForte = () => new LineMaterial({ color: new THREE.Color(0xb0413e), linewidth: 3, depthTest: false, transparent: true });
const CONTORNO_KEYS = ['busto', 'cintura', 'peq_quadril', 'quadril', 'pescoco', 'coxa', 'joelho', 'panturrilha', 'tornozelo', 'braco', 'cotovelo', 'pulso'];

function linha(pts, mat) {
  const g = new LineGeometry(); const arr = [];
  for (const p of pts) arr.push(p[0], p[2], -p[1]);
  g.setPositions(arr);
  const l = new Line2(g, mat); l.computeLineDistances(); l.renderOrder = 10;
  mat.resolution.set(cena.clientWidth, cena.clientHeight);
  return l;
}
function tracos(pts) {   // pequenos traços nas pontas das cotas retas
  const out = [];
  if (pts.length !== 2) return out;
  const a = pts[0], b = pts[1];
  const d = [b[0] - a[0], b[1] - a[1], b[2] - a[2]];
  let t = Math.abs(d[2]) > Math.abs(d[0]) ? [1.4, 0, 0] : [0, 0, 1.4];
  for (const p of [a, b]) out.push([[p[0] - t[0], p[1] - t[1], p[2] - t[2]], [p[0] + t[0], p[1] + t[1], p[2] + t[2]]]);
  return out;
}

let rotuloAtivo = null;
function posicionarRotulo() {   // empurra o rótulo para fora do corpo, conforme a vista
  if (!rotuloAtivo) return;
  const a = rotuloAtivo.lab.position.clone().project(camera);
  const c = rotuloAtivo.eixo.clone().project(camera);
  rotuloAtivo.lab.center.x = a.x >= c.x ? -0.08 : 1.08;
}
function montarCotas() {
  limpar(grupoCotas); rotuloAtivo = null;
  const geo = E.geo; if (!geo) return;
  const mostrar = $('#chkCotas').checked;
  for (const [k, pts] of Object.entries(geo.linhas)) {
    const focado = E.foco === k;
    if (!focado && !(mostrar && CONTORNO_KEYS.includes(k))) continue;
    const mat = focado ? matCotaForte() : matCotaFraca();
    grupoCotas.add(linha(pts, mat));
    if (focado) {
      for (const t of tracos(pts)) grupoCotas.add(linha(t, matCotaForte()));
      const div = document.createElement('div'); div.className = 'rotulo3d';
      div.innerHTML = rotuloCota(k);
      const lab = new CSS2DObject(div);
      // rótulo ao lado da cota, do lado oposto ao braço (não cobre a linha)
      const ladoBraco = (E.med.lado || 'D').toString().toUpperCase().startsWith('E') ? -1 : 1;
      let anc;
      if (pts.length > 3) {
        anc = pts.reduce((m, p) => (p[0] * -ladoBraco > m[0] * -ladoBraco ? p : m), pts[0]);
      } else { const a = pts[0], b = pts[pts.length - 1]; anc = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (a[2] + b[2]) / 2]; }
      lab.center.set(ladoBraco > 0 ? 1.06 : -0.06, 0.5);
      lab.position.copy(P(anc));
      rotuloAtivo = { lab, eixo: new THREE.Vector3(0, anc[2], 0) };
      grupoCotas.add(lab);
    }
  }
}

function valorCampo(k) {
  const v = num(E.med[k]);
  if (v !== null) return { v, est: false };
  const pr = E.proj; if (!pr) return { v: null, est: true };
  if (pr.alvos && pr.alvos[k] !== undefined) return { v: pr.alvos[k], est: true };
  if (pr.usados && pr.usados[k] !== undefined) return { v: pr.usados[k], est: true };
  return { v: null, est: true };
}
function rotuloCota(k) {
  const esc = escMm();
  const r = E.rotulos[k] || NOME_CONT[k] || k;
  let { v, est } = valorCampo(k);
  const usado = E.proj?.usados?.[k];
  let extra = '';
  if (usado !== undefined && v !== null && Math.abs(usado - v) > 0.6) { extra = ` · modelo ${fmt(usado)}`; v = usado; }
  if (v === null) return r;
  return `${r}${est ? ' (estimada)' : ''} · <b>${fmt(v)} cm</b> · ${fmt(v * esc)} mm${extra}`;
}

// ---- câmera
let alvoCam = null;
function vista(v, anim = true) {
  const h = E.proj ? E.proj.landmarks.topo : 150;
  const alvo = new THREE.Vector3(0, h * 0.52, 0);
  const d = h * 2.55;
  const sx = (E.med.lado || 'D') === 'D' ? 1 : -1;
  const pos = {
    frente: new THREE.Vector3(0, h * 0.58, -d), costas: new THREE.Vector3(0, h * 0.58, d),
    lado: new THREE.Vector3(sx * d, h * 0.58, 0), tres: new THREE.Vector3(sx * d * 0.72, h * 0.66, -d * 0.72),
  }[v];
  document.querySelectorAll('#segVista button').forEach((b) => b.setAttribute('aria-pressed', b.dataset.v === v));
  if (!anim) { camera.position.copy(pos); controls.target.copy(alvo); controls.update(); return; }
  alvoCam = { de: camera.position.clone(), para: pos, tde: controls.target.clone(), tpara: alvo, t0: performance.now() };
}
function redimensionar() {
  const w = cena.clientWidth, h = cena.clientHeight;
  renderer.setSize(w, h); css.setSize(w, h);
  camera.aspect = w / h; camera.updateProjectionMatrix();
  grupoCotas.traverse((o) => o.material?.resolution?.set(w, h));
}
new ResizeObserver(redimensionar).observe(cena);
function loop(t) {
  if (alvoCam) {
    const k = Math.min(1, (t - alvoCam.t0) / 450), e = k < .5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;
    camera.position.lerpVectors(alvoCam.de, alvoCam.para, e); controls.target.lerpVectors(alvoCam.tde, alvoCam.tpara, e);
    if (k >= 1) alvoCam = null;
  }
  controls.update(); posicionarRotulo(); renderer.render(scene, camera); css.render(scene, camera);
  requestAnimationFrame(loop);
}

function aplicarAlternar() {
  grade.visible = $('#chkGrade').checked;
  grupoBase.visible = $('#chkBase').checked;
  matCorpo.wireframe = matBraco.wireframe = $('#chkMalha').checked;
  montarCotas();
}

// ============================================================ formulário
function construirCampos() {
  const box = $('#gruposMedidas'); box.innerHTML = '';
  for (const g of E.campos.grupos) {
    const sec = document.createElement('section'); sec.className = 'grupo';
    sec.innerHTML = `<div class="grupo-cab"><span class="tarja" style="background:${CORES_GRUPO[g.id]}"></span>${g.titulo}<span class="contagem" id="cont-${g.id}"></span></div><div class="campos"></div>`;
    const lista = sec.querySelector('.campos');
    for (const c of g.campos) {
      E.rotulos[c.chave] = c.rotulo; E.grupoDe[c.chave] = g.id;
      const row = document.createElement('div'); row.className = 'campo'; row.dataset.k = c.chave;
      row.innerHTML = `<span class="campo-nome" title="${c.descricao}">${c.rotulo}${c.obrigatorio ? '<span class="obr">*</span>' : ''}</span>
        <span class="entrada"><button type="button" data-d="-0.5" aria-label="diminuir">−</button><input inputmode="decimal" aria-label="${c.rotulo}"><span class="un">cm</span><button type="button" data-d="0.5" aria-label="aumentar">+</button></span>
        <span class="estado" title=""></span>`;
      const inp = row.querySelector('input');
      inp.addEventListener('input', () => { const v = num(inp.value); if (v === null) delete E.med[c.chave]; else E.med[c.chave] = v; agendar(); });
      inp.addEventListener('focus', () => focar(c.chave));
      inp.addEventListener('keydown', (ev) => {
        if (ev.key === 'ArrowUp' || ev.key === 'ArrowDown') { ev.preventDefault(); passo(c.chave, ev.key === 'ArrowUp' ? 0.5 : -0.5); }
      });
      row.querySelectorAll('button').forEach((b) => b.addEventListener('click', () => { passo(c.chave, parseFloat(b.dataset.d)); focar(c.chave); }));
      row.addEventListener('mouseenter', () => focar(c.chave, true));
      lista.appendChild(row);
    }
    box.appendChild(sec);
  }
}
function passo(k, d) {
  const base = num(E.med[k]) ?? valorCampo(k).v ?? 0;
  E.med[k] = Math.round((base + d) * 10) / 10;
  const inp = document.querySelector(`.campo[data-k="${k}"] input`); inp.value = fmt(E.med[k]);
  agendar();
}
function focar(k, hover = false) {
  if (E.foco === k) return;
  E.foco = k;
  document.querySelectorAll('.campo').forEach((r) => r.classList.toggle('foco', r.dataset.k === k));
  const desc = E.campos.grupos.flatMap((g) => g.campos).find((c) => c.chave === k);
  const info = $('#infoMedida');
  if (desc) {
    info.hidden = false; $('#infoNome').textContent = desc.rotulo; $('#infoDesc').textContent = desc.descricao;
    const { v, est } = valorCampo(k);
    $('#infoValor').textContent = v === null ? '' : `${fmt(v)} cm${est ? ' (est.)' : ''} · ${fmt(v * escMm())} mm`;
  }
  montarCotas();
}

function preencherFormulario() {
  document.querySelectorAll('.campo').forEach((r) => { const v = E.med[r.dataset.k]; r.querySelector('input').value = v === undefined || v === null ? '' : fmt(v); });
  marcarSeg('#segSexo', (E.med.sexo || 'F').toString().toUpperCase().startsWith('M') ? 'M' : 'F');
  marcarSeg('#segEscala', String(num(E.med.escala) || 5));
  marcarSeg('#segLado', (E.med.lado || 'D').toString().toUpperCase().startsWith('E') ? 'E' : 'D');
  marcarSeg('#segBraco', String(E.med.com_braco || 'Sim').toLowerCase().startsWith('n') ? 'Não' : 'Sim');
  $('#rngAbducao').value = num(E.med.abducao) ?? 15; $('#valAbducao').textContent = `${$('#rngAbducao').value}°`;
  $('#opAbducao').style.opacity = String(E.med.com_braco || 'Sim').toLowerCase().startsWith('n') ? .4 : 1;
  $('#inpNome').value = E.nome;
}
function marcarSeg(sel, v) { document.querySelectorAll(`${sel} button`).forEach((b) => b.setAttribute('aria-pressed', b.dataset.v === v)); }
function ligarSeg(sel, chave, conv = (x) => x) {
  document.querySelectorAll(`${sel} button`).forEach((b) => b.addEventListener('click', () => {
    E.med[chave] = conv(b.dataset.v); marcarSeg(sel, b.dataset.v); preencherFormulario(); agendar();
  }));
}

// ============================================================ prévia
let tPrevia = null, ctrlPrevia = null, primeira = true;
function agendar() { clearTimeout(tPrevia); tPrevia = setTimeout(previa, 160); }
async function previa() {
  ctrlPrevia?.abort(); ctrlPrevia = new AbortController();
  $('#carregando').hidden = false;
  try {
    const r = await fetch('/api/previa', { method: 'POST', body: JSON.stringify({ nome: E.nome, medidas: E.med }), signal: ctrlPrevia.signal });
    const d = await r.json();
    if (d.erro) { mostrarErro(d); return; }
    E.proj = d.projeto; E.geo = d.geo;
    montarCorpo(d.geo); atualizarPainel();
    if (primeira) { vista('tres', false); primeira = false; }
    const ch = $('#estadoPrevia'); ch.className = 'chip chip-ok'; ch.textContent = 'prévia ao vivo';
  } catch (e) { if (e.name !== 'AbortError') console.error(e); }
  finally { $('#carregando').hidden = true; }
}
function mostrarErro(d) {
  const ch = $('#estadoPrevia'); ch.className = 'chip chip-erro'; ch.textContent = 'falta informação';
  const ul = $('#listaAvisos'); ul.innerHTML = '';
  const li = document.createElement('li'); li.className = 'erro'; li.textContent = d.erro; ul.appendChild(li);
  $('#contAvisos').textContent = '!'; $('#contAvisos').className = 'chip chip-erro';
  marcarEstados(d.erro);
}

function marcarEstados(erro = '') {
  const pr = E.proj || {}; const fora = new Set((pr.faixas || []).map((f) => f.chave));
  const est = new Set(pr.estimadas || []);
  const obrig = new Set(E.campos.grupos.flatMap((g) => g.campos).filter((c) => c.obrigatorio).map((c) => c.chave));
  const contagem = {};
  document.querySelectorAll('.campo').forEach((r) => {
    const k = r.dataset.k, v = num(E.med[k]), dot = r.querySelector('.estado'), inp = r.querySelector('input');
    let cls = 'ok', tit = 'Informada';
    if (v === null) {
      if (obrig.has(k)) { cls = 'falta'; tit = 'Obrigatória — preencher'; }
      else { cls = 'est'; tit = 'Vazia: estimada por proporção'; }
    } else if (fora.has(k)) { cls = 'fora'; tit = 'Fora da faixa usual de adultos'; }
    const u = pr.usados?.[k];
    if (v !== null && u !== undefined && Math.abs(u - v) > ({ cint_solo: 3, alt_cava: 2 }[k] ?? 99)) { cls = 'ajust'; tit = `Ajustada no modelo para ${fmt(u)} cm`; }
    dot.className = `estado ${cls}`; dot.title = tit;
    const ve = valorCampo(k);
    inp.placeholder = v === null && ve.v !== null ? `≈ ${fmt(ve.v)}` : '';
    const g = E.grupoDe[k]; contagem[g] = contagem[g] || [0, 0]; contagem[g][1]++; if (v !== null) contagem[g][0]++;
  });
  for (const [g, [a, b]] of Object.entries(contagem)) { const el = $(`#cont-${g}`); if (el) el.textContent = `${a}/${b}`; }
}

function atualizarPainel() {
  const pr = E.proj, geo = E.geo, esc = escMm();
  $('#kpiAltura').textContent = `${fmt(geo.altura_mm, 0)} mm`;
  $('#kpiEscala').textContent = `1:${fmt(pr.escala, 0)}`;
  $('#kpiBase').textContent = `${fmt(110 * esc / 2, 0)} · Ø${fmt(geo.haste.d * esc, 0)}`;
  $('#legendaEscala').innerHTML = `grade: 5 cm do corpo = ${fmt(5 * esc)} mm no manequim<br>${pr.sexo === 'M' ? 'corpo-base masculino' : 'corpo-base feminino'}`;
  // contornos
  const tb = $('#tabContornos tbody'); tb.innerHTML = '';
  const mp = geo.medidas_previa;
  for (const k of ['busto', 'cintura', 'peq_quadril', 'quadril', 'pescoco', 'gancho', 'coxa', 'joelho', 'panturrilha', 'tornozelo', 'braco', 'cotovelo', 'pulso']) {
    if (k === 'braco' && !pr.com_braco) continue;
    const tab = num(E.med[k]);
    const prev = mp[k] !== undefined ? mp[k] : pr.alvos[k];
    const tr = document.createElement('tr');
    if (tab === null) tr.className = 'est';
    else if (Math.abs(prev - tab) > 1) tr.className = 'dif';
    tr.innerHTML = `<td>${NOME_CONT[k]}</td><td>${tab === null ? 'est.' : fmt(tab)}</td><td>${fmt(prev)}</td><td>${fmt(prev * esc)}</td>`;
    tr.addEventListener('mouseenter', () => focar(k, true));
    tb.appendChild(tr);
  }
  // alturas
  const ta = $('#tabAlturas tbody'); ta.innerHTML = '';
  for (const [k, n] of PONTOS) {
    const z = pr.landmarks[k]; if (z === undefined) continue;
    const tr = document.createElement('tr'); tr.innerHTML = `<td>${n}</td><td>${fmt(z)}</td><td>${fmt(z * esc)}</td>`; ta.appendChild(tr);
  }
  // avisos
  const ul = $('#listaAvisos'); ul.innerHTML = '';
  const itens = [];
  for (const f of pr.faixas || []) itens.push(['erro', f.texto]);
  for (const a of pr.avisos || []) itens.push([/Estimadas/.test(a) ? 'info' : 'ajuste', a]);
  if (Math.abs((mp.gancho ?? 0) - (num(E.med.gancho) ?? mp.gancho)) > 2)
    itens.push(['ajuste', `Gancho: a prévia dá ${fmt(mp.gancho)} cm (tabela ${fmt(num(E.med.gancho))}). O gancho não é forçado para não deformar barriga e bumbum.`]);
  if (!itens.length) itens.push(['ok', 'Medidas coerentes entre si.']);
  for (const [c, t] of itens) { const li = document.createElement('li'); li.className = c; li.textContent = t; ul.appendChild(li); }
  const nAv = itens.filter((i) => i[0] !== 'ok' && i[0] !== 'info').length;
  $('#contAvisos').textContent = nAv; $('#contAvisos').className = `chip ${nAv ? 'chip-alerta' : 'chip-ok'}`;
  marcarEstados();
  if (E.foco) { const k = E.foco; E.foco = null; focar(k); }
}

// ============================================================ planilha / pessoas
async function carregarPlanilha(selecionar) {
  const r = await fetch('/api/planilha'); const d = await r.json();
  if (d.erro) { toast(d.erro); return; }
  E.pessoas = d.pessoas;
  const sel = $('#selPessoa'); sel.innerHTML = '';
  for (const [n, m] of Object.entries(E.pessoas)) {
    const o = document.createElement('option'); o.value = n;
    o.textContent = Object.keys(m).length ? n : `${n} (vazia)`; sel.appendChild(o);
  }
  const o = document.createElement('option'); o.value = '__novo'; o.textContent = '+ Nova pessoa'; sel.appendChild(o);
  const alvo = selecionar && E.pessoas[selecionar] ? selecionar : Object.keys(E.pessoas).find((n) => Object.keys(E.pessoas[n]).length > 3) || Object.keys(E.pessoas)[0];
  sel.value = alvo; escolherPessoa(alvo);
}
function escolherPessoa(n) {
  if (n === '__novo') {
    const opc = {}; for (const k of Object.keys(OPCOES_PADRAO)) opc[k] = E.med[k] ?? OPCOES_PADRAO[k];
    E.med = { ...opc }; E.nome = 'Nova'; E.coluna = null;
  } else {
    E.med = { ...OPCOES_PADRAO, ...(E.pessoas[n] || {}) }; E.nome = n; E.coluna = n;
  }
  E.proj = null; preencherFormulario(); agendar();
}

async function salvar() {
  const nome = ($('#inpNome').value || '').trim();
  if (!nome) { toast('Dê um nome para a coluna da planilha.'); return; }
  const r = await fetch('/api/planilha', { method: 'POST', body: JSON.stringify({ nome, medidas: E.med }) });
  const d = await r.json();
  if (d.erro) { toast(d.erro); return; }
  toast(`Coluna "${nome}" salva na planilha.`);
  await carregarPlanilha(nome);
}

// ============================================================ gerar arquivos
async function gerar() {
  const nome = ($('#inpNome').value || '').trim() || 'manequim';
  const r = await fetch('/api/gerar', { method: 'POST', body: JSON.stringify({ nome, medidas: E.med }) });
  const d = await r.json();
  if (d.erro) { toast(d.erro); return; }
  $('#btnGerar').disabled = true; $('#blocoGerar').hidden = false;
  $('#listaArquivos').innerHTML = ''; $('#tabFinal').hidden = true;
  $('#blocoGerar').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  acompanhar(d.job);
}
async function acompanhar(job) {
  const r = await fetch(`/api/job/${job}`); const j = await r.json();
  $('#barra').style.width = `${Math.round((j.fracao || 0) * 100)}%`;
  $('#txtProgresso').textContent = j.texto || '';
  if (j.estado === 'rodando') { setTimeout(() => acompanhar(job), 1000); return; }
  $('#btnGerar').disabled = false;
  if (j.estado === 'erro') { toast('A geração falhou. Veja o aviso no painel.'); return; }
  const res = j.resultado; const esc = escMm();
  const tb = $('#tabFinal tbody'); tb.innerHTML = '';
  for (const k of ['busto', 'cintura', 'peq_quadril', 'quadril', 'pescoco', 'joelho', 'braco', 'cotovelo', 'pulso', 'gancho']) {
    if (res.medidas[k] === undefined) continue;
    const t = num(E.med[k]); const f = res.medidas[k];
    const tr = document.createElement('tr'); if (t !== null && Math.abs(f - t) > 1) tr.className = 'dif';
    tr.innerHTML = `<td>${NOME_CONT[k]}</td><td>${t === null ? 'est.' : fmt(t)}</td><td>${fmt(f)}</td>`; tb.appendChild(tr);
  }
  $('#tabFinal').hidden = false;
  const ul = $('#listaArquivos'); ul.innerHTML = '';
  const tipo = (f) => f.endsWith('.stl') ? (f.includes('montagem') ? 'conferência' : 'peça STL') : f.endsWith('.pdf') ? 'prancha PDF' : 'imagem';
  for (const a of res.arquivos) {
    const li = document.createElement('li');
    li.innerHTML = `<a href="${a.url}" target="_blank" rel="noopener"><span>${a.nome}</span><span>${tipo(a.nome)}</span></a>`;
    ul.appendChild(li);
  }
  toast(`Arquivos prontos: altura ${fmt(res.altura_mm, 0)} mm.`);
}

// ============================================================ início
async function iniciar() {
  E.campos = await (await fetch('/api/campos')).json();
  construirCampos();
  ligarSeg('#segSexo', 'sexo');
  ligarSeg('#segEscala', 'escala', (v) => parseFloat(v));
  ligarSeg('#segLado', 'lado');
  ligarSeg('#segBraco', 'com_braco');
  $('#rngAbducao').addEventListener('input', (e) => { E.med.abducao = parseFloat(e.target.value); $('#valAbducao').textContent = `${e.target.value}°`; agendar(); });
  $('#selPessoa').addEventListener('change', (e) => escolherPessoa(e.target.value));
  $('#inpNome').addEventListener('input', (e) => { E.nome = e.target.value; });
  $('#btnSalvar').addEventListener('click', salvar);
  $('#btnGerar').addEventListener('click', gerar);
  document.querySelectorAll('#segVista button').forEach((b) => b.addEventListener('click', () => vista(b.dataset.v)));
  ['#chkCotas', '#chkGrade', '#chkMalha', '#chkBase'].forEach((s) => $(s).addEventListener('change', aplicarAlternar));
  redimensionar(); vista('tres', false); requestAnimationFrame(loop);
  await carregarPlanilha();
}
window.__manequim = { E, grupoCotas, scene, camera };   // para inspeção no console
iniciar();
