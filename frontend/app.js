const API = "/api";
const root = document.querySelector("#app");
const navItems = ["chat", "evidencia", "calculadoras", "interacciones", "flashcards", "examen", "progreso", "auditoria"];
const calculatorLabels = {
  imc: "Índice de masa corporal",
  superficie_corporal: "Superficie corporal",
  aclaramiento_creatinina: "Aclaramiento de creatinina",
  egfr: "TFG estimada (CKD-EPI)",
  dosis_por_peso: "Dosis por peso",
  ajuste_renal: "Ajuste renal de medicamentos",
};
const calculatorFields = {
  imc: ["peso_kg", "altura_cm"],
  superficie_corporal: ["peso_kg", "altura_cm", "formula"],
  aclaramiento_creatinina: ["edad", "peso_kg", "altura_cm", "creatinina_mg_dl", "sexo"],
  egfr: ["edad", "creatinina_mg_dl", "sexo"],
  dosis_por_peso: ["peso_kg", "mg_por_kg", "dosis_max_mg", "dosis_min_mg", "tomas_por_dia"],
  ajuste_renal: ["farmaco", "aclaramiento_ml_min"],
};
const fieldLabels = {
  peso_kg: "Peso (kg)", altura_cm: "Altura (cm)", formula: "Fórmula", edad: "Edad (años)",
  creatinina_mg_dl: "Creatinina (mg/dL)", sexo: "Sexo", mg_por_kg: "Dosis (mg/kg)",
  dosis_max_mg: "Dosis máxima (mg, opcional)", dosis_min_mg: "Dosis mínima (mg, opcional)",
  tomas_por_dia: "Tomas por día (opcional)", farmaco: "Medicamento",
  aclaramiento_ml_min: "Aclaramiento (mL/min)",
};
const translations = {
  es: { login: "Iniciar sesión", register: "Crear cuenta", username: "Usuario", password: "Contraseña", create: "Necesito crear una cuenta", existing: "Ya tengo una cuenta", app: "Medicine Study AI", newChat: "Nuevo chat", logout: "Salir", upload: "Cargar PDF", chat: "Chat", evidence: "Evidencia", calculators: "Calculadoras", interactions: "Interacciones", flashcards: "Flashcards", exam: "Examen", progress: "Progreso", audit: "Auditoría", send: "Enviar", generating: "Generando respuesta…", useful: "¿Te fue útil?", search: "Buscar", calculate: "Calcular", sources: "Fuentes", process: "Proceso", theme: "Tema oscuro", light: "Tema claro", material: "Generar material", noEvents: "No hay eventos de auditoría para mostrar.", noProgress: "Completa exámenes para ver tu progreso por tema." },
  en: { login: "Sign in", register: "Create account", username: "Username", password: "Password", create: "I need an account", existing: "I already have an account", app: "Medicine Study AI", newChat: "New chat", logout: "Sign out", upload: "Upload PDF", chat: "Chat", evidence: "Evidence", calculators: "Calculators", interactions: "Interactions", flashcards: "Flashcards", exam: "Exam", progress: "Progress", audit: "Audit", send: "Send", generating: "Generating answer…", useful: "Was this useful?", search: "Search", calculate: "Calculate", sources: "Sources", process: "Process", theme: "Dark theme", light: "Light theme", material: "Generate material", noEvents: "No audit events to show.", noProgress: "Complete exams to see progress by topic." },
  fr: { login: "Se connecter", register: "Créer un compte", username: "Utilisateur", password: "Mot de passe", create: "Créer un compte", existing: "J’ai déjà un compte", app: "Medicine Study AI", newChat: "Nouveau chat", logout: "Se déconnecter", upload: "Charger un PDF", chat: "Chat", evidence: "Preuves", calculators: "Calculateurs", interactions: "Interactions", flashcards: "Fiches", exam: "Examen", progress: "Progression", audit: "Audit", send: "Envoyer", generating: "Génération…", useful: "Cette réponse vous a-t-elle aidé ?", search: "Rechercher", calculate: "Calculer", sources: "Sources", process: "Processus", theme: "Thème sombre", light: "Thème clair", material: "Générer", noEvents: "Aucun événement d’audit.", noProgress: "Complétez des examens pour voir la progression." },
  de: { login: "Anmelden", register: "Konto erstellen", username: "Benutzername", password: "Passwort", create: "Ich brauche ein Konto", existing: "Ich habe bereits ein Konto", app: "Medicine Study AI", newChat: "Neuer Chat", logout: "Abmelden", upload: "PDF laden", chat: "Chat", evidence: "Evidenz", calculators: "Rechner", interactions: "Interaktionen", flashcards: "Karteikarten", exam: "Prüfung", progress: "Fortschritt", audit: "Audit", send: "Senden", generating: "Antwort wird erstellt…", useful: "War das hilfreich?", search: "Suchen", calculate: "Berechnen", sources: "Quellen", process: "Prozess", theme: "Dunkles Thema", light: "Helles Thema", material: "Material erzeugen", noEvents: "Keine Audit-Ereignisse.", noProgress: "Prüfungen abschließen, um Fortschritt zu sehen." },
  zh: { login: "登录", register: "创建账户", username: "用户名", password: "密码", create: "我需要创建账户", existing: "我已有账户", app: "Medicine Study AI", newChat: "新对话", logout: "退出", upload: "上传 PDF", chat: "对话", evidence: "证据", calculators: "计算器", interactions: "药物相互作用", flashcards: "闪卡", exam: "考试", progress: "进度", audit: "审计", send: "发送", generating: "正在生成回答…", useful: "回答有帮助吗？", search: "搜索", calculate: "计算", sources: "来源", process: "过程", theme: "深色主题", light: "浅色主题", material: "生成材料", noEvents: "暂无审计事件。", noProgress: "完成考试后查看主题进度。" },
};

const state = {
  user: JSON.parse(localStorage.getItem("msai-user") || "null"),
  authMode: "login", authError: "", language: localStorage.getItem("msai-language") || "es",
  theme: localStorage.getItem("msai-theme") || "dark", options: null, section: "chat",
  messages: [], input: "", papers: [], sources: [], process: [], factuality: null, icd: null,
  contradictions: [], chats: [], chatId: crypto.randomUUID(), chatTitle: "Nuevo chat", busy: false,
  error: "", settings: { pubmed: true, evidence: "todo", factuality: true },
  cards: [], questions: [], examIndex: 0, examSelected: null, examScore: 0, audit: [], progress: null, uploadStatus: "", calculator: { operation: "imc", params: {
    peso_kg: "70", altura_cm: "175", edad: "40", creatinina_mg_dl: "1", sexo: "M",
    formula: "mosteller", mg_por_kg: "10", dosis_max_mg: "", dosis_min_mg: "",
    tomas_por_dia: "", farmaco: "vancomicina", aclaramiento_ml_min: "45",
  }, result: null, busy: false }, studyTopic: "", interactionText: "warfarina\nibuprofeno", interactionResult: null,
};

function copy() { return translations[state.language] || translations.es; }
function esc(value) { return String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" })[char]); }
function text(value) { return esc(value).replace(/\n/g, "<br>"); }
function markdown(value) {
  let html = esc(value || "").replace(/^### (.+)$/gm, "<h4>$1</h4>").replace(/^## (.+)$/gm, "<h3>$1</h3>").replace(/^# (.+)$/gm, "<h2>$1</h2>");
  html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>").replace(/\*(.+?)\*/g, "<em>$1</em>").replace(/`([^`]+)`/g, "<code>$1</code>");
  html = html.replace(/\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
  return html.split(/\n{2,}/).map((part) => part.startsWith("<h") ? part : `<p>${part.replace(/\n/g, "<br>")}</p>`).join("");
}
async function request(path, init = {}) {
  const response = await fetch(`${API}${path}`, init);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || "La operación no se pudo completar.");
  return data;
}
function setUser(user) {
  state.user = user; localStorage.setItem("msai-user", JSON.stringify(user));
  if (user) { refreshChats(); loadUserData(); }
  render();
}
async function loadUserData() {
  try {
    const [cards, progress] = await Promise.all([
      request(`/flashcards?usuario_id=${state.user.usuario_id}&pendientes=true`),
      request(`/progreso?usuario_id=${state.user.usuario_id}`),
    ]);
    state.cards = cards.flashcards || []; state.progress = progress; render();
  } catch (error) { state.error = error.message; render(); }
}
async function refreshChats() {
  if (!state.user) return;
  try { state.chats = await request(`/chats?usuario_id=${state.user.usuario_id}`); render(); } catch (error) { state.error = error.message; render(); }
}
function resetChat() {
  Object.assign(state, { section: "chat", messages: [], papers: [], sources: [], process: [], factuality: null, icd: null, contradictions: [], error: "", chatId: crypto.randomUUID(), chatTitle: "Nuevo chat" });
  render();
}
function resultFields(result) {
  return `<dl class="result-grid">${Object.entries(result || {}).map(([key, value]) => `<div class="result-item"><dt>${esc(key.replaceAll("_", " "))}</dt><dd>${Array.isArray(value) ? value.map((item) => `<span>${esc(typeof item === "object" ? JSON.stringify(item) : item)}</span>`).join("") : esc(typeof value === "object" ? JSON.stringify(value) : value)}</dd></div>`).join("")}</dl>`;
}
function panel(title, body) { return `<section class="panel"><h2>${esc(title)}</h2>${body}</section>`; }
function renderLogin() {
  const c = copy();
  return `<main class="auth-shell"><form class="panel auth-card" data-form="auth"><div class="brand-mark">✚</div><h1 class="title">${c.app}</h1><p class="muted">Asistente de estudio médico con evidencia verificable.</p><label>${c.username}<input name="usuario" required minlength="3" autocomplete="username"></label><label>${c.password}<input name="password" required minlength="4" type="password" autocomplete="${state.authMode === "login" ? "current-password" : "new-password"}"></label><button class="button primary" type="submit">${state.authMode === "login" ? c.login : c.register}</button><button class="link-button" type="button" data-action="toggle-auth">${state.authMode === "login" ? c.create : c.existing}</button>${state.authError ? `<p class="alert warning">${esc(state.authError)}</p>` : ""}</form></main>`;
}
function renderShell() {
  const c = copy();
  const labels = { chat: c.chat, evidencia: c.evidence, calculadoras: c.calculators, interacciones: c.interactions, flashcards: c.flashcards, examen: c.exam, progreso: c.progress, auditoria: c.audit };
  return `<main class="app-shell"><header class="app-header"><div><h1 class="title">${c.app}</h1><p class="muted small">👤 ${esc(state.user.usuario)} · ${state.language}</p></div><div class="header-actions"><label class="button secondary">${c.upload}<input id="pdf-upload" type="file" accept=".pdf,application/pdf" hidden></label><button class="button secondary" data-action="theme">${state.theme === "dark" ? c.light : c.theme}</button><button class="button secondary" data-action="logout">${c.logout}</button></div></header><div class="layout"><aside class="sidebar"><button class="button primary full" data-action="new-chat">＋ ${c.newChat}</button><label class="muted small">${c.language || "Idioma"}<select id="language">${(state.options?.idiomas || [{ codigo: "es", nombre: "Español" }, { codigo: "en", nombre: "English" }, { codigo: "fr", nombre: "Français" }, { codigo: "de", nombre: "Deutsch" }, { codigo: "zh", nombre: "中文" }]).map((item) => `<option value="${item.codigo}" ${item.codigo === state.language ? "selected" : ""}>${esc(item.nombre)}</option>`).join("")}</select></label><label class="check"><input id="pubmed" type="checkbox" ${state.settings.pubmed ? "checked" : ""}> ${c.pubmed || "Búsqueda PubMed"}</label><label class="muted small">Nivel de evidencia<select id="evidence">${(state.options?.modos_evidencia || ["todo"]).map((item) => `<option ${item === state.settings.evidence ? "selected" : ""}>${esc(item)}</option>`).join("")}</select></label><label class="check"><input id="factuality" type="checkbox" ${state.settings.factuality ? "checked" : ""}> ${c.verify || "Verificar factualidad"}</label><label class="check"><input id="dark-toggle" type="checkbox" ${state.theme === "dark" ? "checked" : ""}> ${state.theme === "dark" ? c.darkMode || "Tema oscuro" : c.lightMode || "Tema claro"}</label><div class="sidebar-block"><strong>Historial</strong>${state.chats.length ? state.chats.map((chat) => `<div class="chat-row"><button class="history-button" data-action="load-chat" data-id="${esc(chat.id)}">${esc(chat.titulo)}</button><button class="icon-button danger" data-action="delete-chat" data-id="${esc(chat.id)}">×</button></div>`).join("") : '<p class="muted small">Aún no hay chats guardados.</p>'}</div><div class="sidebar-status muted small">${esc(state.uploadStatus || "PDF: OCR, extracción de tablas y RAG disponibles.")}</div></aside><section class="content"><nav class="tabs">${navItems.map((item) => `<button class="tab ${state.section === item ? "active" : ""}" data-action="section" data-section="${item}">${labels[item]}</button>`).join("")}</nav><div class="content-inner">${renderSection()}</div></section></div></main>`;
}
function renderSection() {
  switch (state.section) {
    case "evidencia": return renderEvidence();
    case "calculadoras": return renderCalculator();
    case "interacciones": return renderInteractions();
    case "flashcards": return renderMaterial("Flashcards", state.cards, true);
    case "examen": return renderExam();
    case "progreso": return renderProgress();
    case "auditoria": return renderAudit();
    default: return renderChat();
  }
}
function renderChat() {
  const c = copy();
  const messages = state.messages.length ? state.messages.map((message, index) => `<article class="message ${message.role === "user" ? "user" : "assistant"}">${message.role === "assistant" ? markdown(message.content || c.generating) : `<p>${text(message.content)}</p>`}${message.role === "assistant" && message.content ? `<div class="feedback"><span class="muted small">${c.useful}</span><button class="feedback-button" data-action="feedback" data-index="${index}" data-value="1">👍</button><button class="feedback-button" data-action="feedback" data-index="${index}" data-value="-1">👎</button></div>` : ""}</article>`).join("") : `<div class="empty-state"><div class="brand-mark">✚</div><h2 class="title">${c.app}</h2><p class="muted">Consulta temas médicos, activa evidencia PubMed o carga tus PDFs.</p></div>`;
  const process = state.process.length ? state.process.map((item) => `<p class="small muted">✓ ${esc(item)}</p>`).join("") : `<p class="small muted">Los pasos del turno aparecerán aquí.</p>`;
  const sourceItems = (state.sources.length ? state.sources : state.papers).map((item, index) => `<div class="source-row"><strong>${esc(item.titulo || item.fuente || `Fuente ${index + 1}`)}</strong><p class="muted small">${esc(item.resumen || item.texto || "")}</p></div>`).join("");
  return `<section class="chat-grid"><div class="panel chat-panel"><div class="messages">${messages}</div>${state.error ? `<p class="alert warning">${esc(state.error)}</p>` : ""}<form class="composer" data-form="chat"><textarea name="mensaje" rows="3" placeholder="Pregunta médica o escribe un tema para materiales…" ${state.busy ? "disabled" : ""}>${esc(state.input)}</textarea><button class="button primary" ${state.busy ? "disabled" : ""}>${state.busy ? c.generating : c.send}</button></form></div><aside class="side-panels">${panel(c.process, process)}${state.factuality ? panel("Verificación de factualidad", resultFields(state.factuality)) : ""}${state.contradictions.length ? '<p class="alert warning">⚠ Contradicciones fisiológicas detectadas.</p>' : ""}${state.icd ? `<p class="alert info">ICD-11: ${(state.icd.terminos_encontrados || []).length} términos.</p>` : ""}${panel(c.sources, sourceItems || '<p class="muted small">Las fuentes aparecerán aquí.</p>')}</aside></section>`;
}
function renderEvidence() {
  const providers = ["pubmed", "europepmc", "semantic-scholar"];
  return `<div class="stack">${panel("PubMed, Europe PMC y evidencia", `<form class="search-form" data-form="evidence"><input name="consulta" required minlength="2" placeholder="Consulta científica"><select name="provider">${providers.map((item) => `<option value="${item}">${item === "semantic-scholar" ? "Semantic Scholar" : item === "europepmc" ? "Europe PMC" : "PubMed"}</option>`).join("")}</select><button class="button primary">${copy().search}</button></form>`)}<div class="paper-grid">${state.papers.map((paper) => `<article class="paper-card"><h3>${esc(paper.titulo)}</h3><p class="muted">${esc(paper.resumen || "")}</p><small>${esc(paper.pmid ? `PMID: ${paper.pmid}` : paper.doi || "")} · ${esc(paper.revista || "")} · ${esc(paper.anio || "")}</small></article>`).join("")}</div></div>`;
}
function renderCalculator() {
  const c = state.calculator;
  const fields = calculatorFields[c.operation] || [];
  const controls = fields.map((key) => `<label>${fieldLabels[key] || key.replaceAll("_", " ")}${key === "sexo" ? `<select data-param="${key}"><option value="M" ${c.params[key] === "M" ? "selected" : ""}>Masculino</option><option value="F" ${c.params[key] === "F" ? "selected" : ""}>Femenino</option></select>` : key === "formula" ? `<select data-param="${key}"><option value="mosteller">Mosteller</option><option value="dubois">Du Bois & Du Bois</option></select>` : `<input data-param="${key}" ${["dosis_max_mg", "dosis_min_mg", "tomas_por_dia"].includes(key) ? "" : "required"} type="${key === "farmaco" ? "text" : "number"}" step="any" value="${esc(c.params[key] || "")}">`}</label>`).join("");
  return panel(copy().calculators, `<form class="calculator-form" data-form="calculator"><label>Calculadora<select data-param="operation">${Object.entries(calculatorLabels).map(([key, label]) => `<option value="${key}" ${key === c.operation ? "selected" : ""}>${label}</option>`).join("")}</select></label><div class="form-grid">${controls}</div><button class="button primary">${c.busy ? "Calculando…" : copy().calculate}</button></form>${c.result ? `<div class="result-card ${c.result.error ? "error" : ""}"><h3>${c.result.error ? "No se pudo calcular" : "Resultado"}</h3>${c.result.error ? `<p>${esc(c.result.error)}</p>` : resultFields(c.result)}</div>` : ""}`);
}
function renderInteractions() {
  return panel(copy().interactions, `<label>Un medicamento por línea<textarea id="interaction-text" rows="5">${esc(state.interactionText)}</textarea></label><div class="button-row"><button class="button primary" data-action="check-interactions">Verificar base local</button><button class="button violet" data-action="ask-interactions">Consultar IA si no hay datos</button></div>${state.interactionResult ? `<div class="result-card">${resultFields(state.interactionResult)}</div>` : ""}`);
}
function renderMaterial(title, items, flashcards) {
  return panel(title, `<div class="material-input"><input id="study-topic" value="${esc(state.studyTopic)}" placeholder="Tema o texto fuente"><button class="button primary" data-action="generate" data-kind="${flashcards ? "flashcards" : "examenes"}">${copy().material}</button></div><div class="material-grid">${items.map((item, index) => `<article class="material-card"><strong>${esc(item.pregunta || item.question || "")}</strong><details><summary>Mostrar respuesta</summary><p>${esc(item.respuesta || item.explicacion || item.answer || "")}</p>${flashcards ? `<div class="button-row">${["otra_vez", "dificil", "bien", "facil"].map((button) => `<button class="small-button" data-action="review" data-id="${item.id}" data-button="${button}">${button}</button>`).join("")}</div>` : ""}</details></article>`).join("")}</div>`);
}
function renderExam() {
  const current = state.questions[state.examIndex];
  let body = `<div class="material-input"><input id="study-topic" value="${esc(state.studyTopic)}" placeholder="Tema o texto fuente"><button class="button primary" data-action="generate" data-kind="examenes">Generar examen</button></div>`;
  if (!state.questions.length) body += '<p class="muted">Genera un examen para comenzar.</p>';
  else if (!current) body += `<p class="success-text">Examen terminado: ${state.examScore}/${state.questions.length} correctas.</p>`;
  else body += `<article class="exam-card"><p class="muted small">Pregunta ${state.examIndex + 1} de ${state.questions.length}</p><h3>${esc(current.pregunta)}</h3><div class="exam-options">${(current.opciones || []).map((option, index) => {
    const className = state.examSelected === null ? "" : index === current.respuesta_correcta ? "correct" : index === state.examSelected ? "incorrect" : "";
    return `<button class="exam-option ${className}" data-action="answer-exam" data-index="${index}" ${state.examSelected !== null ? "disabled" : ""}>${esc(option)}</button>`;
  }).join("")}</div>${state.examSelected !== null ? `<p class="muted">${esc(current.explicacion || "")}</p><button class="button primary" data-action="next-exam">Siguiente</button>` : ""}</article>`;
  return panel(copy().exam, body);
}
function renderProgress() {
  const data = state.progress;
  if (!data) return panel(copy().progress, `<p class="muted">${copy().noProgress}</p>`);
  const summary = data.resumen || {};
  const stats = [["Temas estudiados", summary.n_temas], ["Flashcards", summary.n_flashcards], ["Preguntas", summary.n_preguntas], ["Intentos", summary.n_intentos]];
  const topics = Array.isArray(data.temas) ? data.temas : [];
  return panel(copy().progress, `<div class="stats-grid result-grid">${stats.map(([label, value]) => `<div class="result-item"><dt>${label}</dt><dd class="stat-value">${esc(value ?? 0)}</dd></div>`).join("")}</div><h3>Temas estudiados</h3>${topics.length ? `<div class="topic-list">${topics.map((item) => { const percentage = Math.round((item.porcentaje || 0) * 100); return `<div class="topic-row"><span>${esc(item.tema || "Tema")}</span><strong>${percentage}%</strong><progress max="100" value="${percentage}"></progress></div>`; }).join("")}</div>` : `<p class="muted">${copy().noProgress}</p>`}`);
}
function renderAudit() {
  const body = state.audit.length ? state.audit.map((item) => `<article class="audit-row"><div><strong>${esc(item.tipo_evento ? item.tipo_evento.replaceAll("_", " ") : "Actividad")}</strong><span class="muted small">${esc(item.fecha || item.timestamp || "")}</span></div><p class="muted small">${esc(item.resumen || item.descripcion || "Evento registrado sin detalles médicos.")}</p></article>`).join("") : `<p class="muted">${copy().noEvents}</p>`;
  return panel(copy().audit, body);
}
function render() {
  document.documentElement.dataset.theme = state.theme;
  document.documentElement.lang = state.language;
  root.innerHTML = state.user ? renderShell() : renderLogin();
}
async function authenticate(form) {
  try {
    const data = await request(`/auth/${state.authMode}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ usuario: form.usuario.value.trim(), password: form.password.value }) });
    state.authError = ""; setUser(data);
  } catch (error) { state.authError = error.message; render(); }
}
async function sendChat(form) {
  const message = form.mensaje.value.trim();
  if (!message || state.busy || !state.user) return;
  state.input = ""; state.busy = true; state.error = ""; state.process = [];
  state.messages.push({ role: "user", content: message }, { role: "assistant", content: "", question: message }); render();
  try {
    const response = await fetch(`${API}/chat/stream`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({
      mensaje: message, usuario_id: state.user.usuario_id, idioma: state.language, historial: state.messages.slice(0, -2),
      buscar_pubmed: state.settings.pubmed, modo_evidencia: state.settings.evidence, verificar_factualidad: state.settings.factuality, chat_id: state.chatId,
    }) });
    if (!response.body) throw new Error("El navegador no soporta streaming.");
    const reader = response.body.getReader(); const decoder = new TextDecoder(); let buffer = ""; let finalText = "";
    const consume = (chunk) => {
      for (const event of chunk.split("\n\n")) {
        const name = event.match(/^event: (.+)$/m)?.[1]; const raw = event.match(/^data: (.+)$/m)?.[1]; if (!raw) continue;
        const data = JSON.parse(raw);
        if (name === "token" || name === "emergency") { finalText += data.content || ""; state.messages[state.messages.length - 1].content = finalText; }
        else if (name === "done") { finalText = data.content || finalText; state.messages[state.messages.length - 1].content = finalText; }
        else if (name === "persistence") { state.chatTitle = data.titulo || state.chatTitle; }
        else if (name === "evidence") { state.papers = data.papers || []; state.process.push(`PubMed: ${state.papers.length} fuentes`); }
        else if (name === "retrieval") state.process.push(`PDF/RAG: ${data.fragmentos} fragmentos recuperados`);
        else if (name === "risk" || name === "error" || name === "warning") state.error = data.message;
        else if (name === "icd11") { state.icd = data; state.process.push(`ICD-11: ${(data.terminos_encontrados || []).length} términos`); }
        else if (name === "sources") state.sources = data.fuentes || [];
        else if (name === "factuality") state.factuality = data;
        else if (name === "physiology") state.contradictions = data.contradicciones || [];
      }
      render();
    };
    while (true) { const { value, done } = await reader.read(); if (done) break; buffer += decoder.decode(value, { stream: true }); const chunks = buffer.split("\n\n"); buffer = chunks.pop() || ""; consume(chunks.join("\n\n")); }
    if (state.chatId) await refreshChats();
  } catch (error) { state.error = error.message; }
  state.busy = false; render();
}
async function uploadPdf(input) {
  if (!input.files?.[0]) return;
  const body = new FormData(); body.append("usuario_id", state.user.usuario_id); body.append("archivo", input.files[0]); state.uploadStatus = "Procesando PDF, OCR, tablas y seguridad…"; render();
  try { const result = await request("/uploads/pdf", { method: "POST", body }); state.uploadStatus = `${result.nombre}: ${result.fragmentos} fragmentos, ${result.tablas_indexadas} tablas indexadas${result.resumen_alertas ? ` · ${result.resumen_alertas}` : ""}`; } catch (error) { state.uploadStatus = error.message; }
  input.value = ""; render();
}

root.addEventListener("submit", async (event) => {
  event.preventDefault(); const form = event.target;
  if (form.dataset.form === "auth") return authenticate(form);
  if (form.dataset.form === "chat") return sendChat(form);
  if (form.dataset.form === "evidence") {
    try { const data = await request(`/search/${form.provider.value}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ usuario_id: state.user.usuario_id, consulta: form.consulta.value, idioma: state.language, modo_evidencia: state.settings.evidence, limite: 20 }) }); state.papers = data.papers || []; render(); } catch (error) { state.error = error.message; render(); }
  }
  if (form.dataset.form === "calculator") {
    state.calculator.busy = true; render();
    try { state.calculator.result = await request("/calculadoras", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ operacion: state.calculator.operation, parametros: state.calculator.params }) }); } catch (error) { state.calculator.result = { error: error.message }; }
    state.calculator.busy = false; render();
  }
});
root.addEventListener("change", async (event) => {
  const target = event.target;
  if (target.id === "pdf-upload") return uploadPdf(target);
  if (target.id === "language") { state.language = target.value; localStorage.setItem("msai-language", state.language); return render(); }
  if (target.id === "pubmed") { state.settings.pubmed = target.checked; return; }
  if (target.id === "factuality") { state.settings.factuality = target.checked; return; }
  if (target.id === "evidence") { state.settings.evidence = target.value; return; }
  if (target.id === "dark-toggle") { state.theme = target.checked ? "dark" : "light"; localStorage.setItem("msai-theme", state.theme); return render(); }
  if (target.dataset.param) { if (target.dataset.param === "operation") state.calculator.operation = target.value; else state.calculator.params[target.dataset.param] = target.value; state.calculator.result = null; return render(); }
});
root.addEventListener("input", (event) => {
  const target = event.target;
  if (target.id === "interaction-text") state.interactionText = target.value;
  if (target.id === "study-topic") state.studyTopic = target.value;
});
root.addEventListener("click", async (event) => {
  const action = event.target.closest("[data-action]")?.dataset.action; if (!action) return;
  if (action === "toggle-auth") { state.authMode = state.authMode === "login" ? "register" : "login"; render(); }
  if (action === "logout") { localStorage.removeItem("msai-user"); state.user = null; render(); }
  if (action === "theme") { state.theme = state.theme === "dark" ? "light" : "dark"; localStorage.setItem("msai-theme", state.theme); render(); }
  if (action === "new-chat") resetChat();
  if (action === "section") {
    state.section = event.target.closest("[data-section]").dataset.section;
    if (state.section === "auditoria") request(`/auditoria?usuario_id=${state.user.usuario_id}`).then((data) => { state.audit = data || []; render(); }).catch(() => {});
    render();
  }
  if (action === "load-chat") { try { const id = event.target.closest("[data-id]").dataset.id; const data = await request(`/chats/${encodeURIComponent(id)}?usuario_id=${state.user.usuario_id}`); state.chatId = id; state.messages = data.mensajes || []; state.section = "chat"; render(); } catch (error) { state.error = error.message; render(); } }
  if (action === "delete-chat") { const id = event.target.closest("[data-id]").dataset.id; await request(`/chats/${encodeURIComponent(id)}?usuario_id=${state.user.usuario_id}`, { method: "DELETE" }); if (id === state.chatId) resetChat(); else refreshChats(); }
  if (action === "feedback") { try { const index = Number(event.target.closest("[data-index]").dataset.index); const message = state.messages[index]; await request("/feedback", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ usuario_id: state.user.usuario_id, chat_id: state.chatId, pregunta: message.question || "", respuesta: message.content, valoracion: Number(event.target.closest("[data-value]").dataset.value), fuentes: state.sources, idioma: state.language }) }); event.target.textContent = "✓"; } catch (error) { state.error = error.message; render(); } }
  if (action === "check-interactions") { try { state.interactionResult = await request("/interacciones", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ farmacos: state.interactionText.split("\n").map((x) => x.trim()).filter(Boolean), idioma: state.language }) }); render(); } catch (error) { state.error = error.message; render(); } }
  if (action === "ask-interactions") { const drugs = state.interactionText.split("\n").map((x) => x.trim()).filter(Boolean); if (drugs.length < 2) return; try { state.interactionResult = await request("/interacciones/ia", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ farmaco_a: drugs[0], farmaco_b: drugs[1], idioma: state.language }) }); render(); } catch (error) { state.error = error.message; render(); } }
  if (action === "generate") { if (!state.studyTopic.trim()) { state.error = "Escribe un tema en el campo de materiales."; return render(); } try { const kind = event.target.closest("[data-kind]").dataset.kind; const data = await request(`/${kind}/generate`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ usuario_id: state.user.usuario_id, texto_fuente: state.studyTopic, tema: state.studyTopic, idioma: state.language, n: 5 }) }); if (kind === "flashcards") state.cards = data.flashcards || []; else { state.questions = data.preguntas || []; state.examIndex = 0; state.examSelected = null; state.examScore = 0; } state.error = data.diagnostico || "Material generado."; render(); } catch (error) { state.error = error.message; render(); } }
  if (action === "answer-exam") {
    const current = state.questions[state.examIndex]; if (!current || state.examSelected !== null) return;
    const selected = Number(event.target.closest("[data-index]").dataset.index); state.examSelected = selected;
    const correct = selected === current.respuesta_correcta; if (correct) state.examScore += 1;
    try { await request("/examenes/attempt", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ usuario_id: state.user.usuario_id, pregunta_id: current.id, correcta: correct }) }); } catch (error) { state.error = error.message; }
    render();
  }
  if (action === "next-exam") { state.examIndex += 1; state.examSelected = null; render(); }
  if (action === "review") { const button = event.target.closest("[data-button]"); try { await request("/flashcards/review", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ usuario_id: state.user.usuario_id, flashcard_id: Number(button.dataset.id), boton: button.dataset.button }) }); button.disabled = true; } catch (error) { state.error = error.message; render(); } }
});

request("/options").then((options) => { state.options = options; render(); }).catch(() => render());
render();
