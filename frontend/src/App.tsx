import { ChangeEvent, FormEvent, ReactNode, useEffect, useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

type Message = { role: "user" | "assistant"; content: string; question?: string; feedback?: number };
type User = { usuario_id: number; usuario: string };
type Paper = { titulo?: string; resumen?: string; pmid?: string; doi?: string; revista?: string; anio?: string };
type Chat = { id: string; titulo: string };
type Options = { idiomas: { codigo: string; nombre: string }[]; modos_evidencia: string[]; limites: Record<string, unknown> };
const API = "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, init);
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail ?? "La operación no se pudo completar.");
  return data;
}

function App() {
  const [user, setUser] = useState<User | null>(() => {
    try { return JSON.parse(localStorage.getItem("msai-user") ?? "null"); } catch { return null; }
  });
  const [authMode, setAuthMode] = useState<"login" | "register">("login");
  const [auth, setAuth] = useState({ usuario: "", password: "" });
  const [options, setOptions] = useState<Options | null>(null);
  const [language, setLanguage] = useState("es");
  const [section, setSection] = useState("chat");
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [papers, setPapers] = useState<Paper[]>([]);
  const [sources, setSources] = useState<any[]>([]);
  const [process, setProcess] = useState<string[]>([]);
  const [factuality, setFactuality] = useState<any>(null);
  const [icd, setIcd] = useState<any>(null);
  const [contradictions, setContradictions] = useState<any[]>([]);
  const [chats, setChats] = useState<Chat[]>([]);
  const [chatId, setChatId] = useState<string>(() => crypto.randomUUID());
  const [chatTitle, setChatTitle] = useState("Nuevo chat");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [settings, setSettings] = useState({ pubmed: true, evidence: "todo", factuality: true, dark: true });
  const [cards, setCards] = useState<any[]>([]);
  const [questions, setQuestions] = useState<any[]>([]);
  const [progress, setProgress] = useState<any>(null);
  const [uploadStatus, setUploadStatus] = useState("");

  useEffect(() => {
    request<Options>("/options").then(setOptions).catch(() => {});
  }, []);

  useEffect(() => {
    if (!user) return;
    refreshChats();
    request<any>(`/flashcards?usuario_id=${user.usuario_id}&pendientes=true`).then((data) => setCards(data.flashcards ?? [])).catch(() => {});
    request<any>(`/progreso?usuario_id=${user.usuario_id}`).then(setProgress).catch(() => {});
  }, [user]);

  async function refreshChats() {
    if (user) setChats(await request<Chat[]>(`/chats?usuario_id=${user.usuario_id}`));
  }

  async function authenticate(event: FormEvent) {
    event.preventDefault();
    try {
      const result = await request<User>(`/auth/${authMode}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(auth) });
      localStorage.setItem("msai-user", JSON.stringify(result));
      setUser(result); setError("");
    } catch (err) { setError(err instanceof Error ? err.message : "No se pudo autenticar."); }
  }

  function resetChat() {
    setChatId(crypto.randomUUID()); setChatTitle("Nuevo chat"); setMessages([]);
    setPapers([]); setSources([]); setProcess([]); setFactuality(null); setIcd(null); setContradictions([]);
    setError(""); setSection("chat");
  }

  async function loadChat(id: string) {
    if (!user) return;
    try {
      const result = await request<{ id: string; mensajes: Message[] }>(`/chats/${encodeURIComponent(id)}?usuario_id=${user.usuario_id}`);
      setChatId(id); setMessages(result.mensajes); setSection("chat");
      setChatTitle(chats.find((chat) => chat.id === id)?.titulo ?? "Chat");
    } catch (err) { setError(err instanceof Error ? err.message : "No se pudo cargar el chat."); }
  }

  async function deleteChat(id: string) {
    if (!user) return;
    await request(`/chats/${encodeURIComponent(id)}?usuario_id=${user.usuario_id}`, { method: "DELETE" });
    if (id === chatId) resetChat();
    await refreshChats();
  }

  async function send(event: FormEvent) {
    event.preventDefault();
    const text = input.trim();
    if (!text || busy || !user) return;
    setInput(""); setBusy(true); setError(""); setProcess([]);
    const nextMessages = [...messages, { role: "user" as const, content: text }, { role: "assistant" as const, content: "", question: text }];
    setMessages(nextMessages);
    try {
      const response = await fetch(`${API}/chat/stream`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({
        mensaje: text, usuario_id: user.usuario_id, idioma: language, historial: messages,
        buscar_pubmed: settings.pubmed, modo_evidencia: settings.evidence, verificar_factualidad: settings.factuality,
      }) });
      if (!response.body) throw new Error("El navegador no soporta streaming.");
      const reader = response.body.getReader(); const decoder = new TextDecoder(); let buffer = ""; let finalText = "";
      while (true) {
        const { value, done } = await reader.read(); if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const chunks = buffer.split("\n\n"); buffer = chunks.pop() ?? "";
        for (const chunk of chunks) {
          const eventName = chunk.match(/^event: (.+)$/m)?.[1];
          const raw = chunk.match(/^data: (.+)$/m)?.[1]; if (!raw) continue;
          const data = JSON.parse(raw);
          if (eventName === "token" || eventName === "emergency") {
            finalText += data.content ?? "";
            setMessages((current) => current.map((item, index) => index === current.length - 1 ? { ...item, content: finalText } : item));
          } else if (eventName === "done") {
            finalText = data.content ?? finalText;
            setMessages((current) => current.map((item, index) => index === current.length - 1 ? { ...item, content: finalText } : item));
          } else if (eventName === "evidence") { setPapers(data.papers ?? []); setProcess((p) => [...p, `PubMed: ${data.papers?.length ?? 0} fuentes (${data.estado?.estado ?? "ok"})`]); }
          else if (eventName === "retrieval") setProcess((p) => [...p, `PDF/RAG: ${data.fragmentos} fragmentos recuperados`]);
          else if (eventName === "risk") setError(data.message);
          else if (eventName === "icd11") { setIcd(data); setProcess((p) => [...p, `ICD-11: ${data.terminos_encontrados?.length ?? 0} términos`]); }
          else if (eventName === "sources") setSources(data.fuentes ?? []);
          else if (eventName === "factuality") setFactuality(data);
          else if (eventName === "physiology") setContradictions(data.contradicciones ?? []);
          else if (eventName === "error" || eventName === "warning") setError(data.message);
        }
      }
      const saved = [...nextMessages.slice(0, -1), { role: "assistant" as const, content: finalText, question: text }];
      setMessages(saved);
      await request(`/chats/${encodeURIComponent(chatId)}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ usuario_id: user.usuario_id, titulo: chatTitle, mensajes: saved }) });
      await refreshChats();
    } catch (err) { setError(err instanceof Error ? err.message : "No se pudo enviar la consulta."); }
    finally { setBusy(false); }
  }

  async function upload(event: ChangeEvent<HTMLInputElement>) {
    if (!user || !event.target.files?.[0]) return;
    const body = new FormData(); body.append("usuario_id", String(user.usuario_id)); body.append("archivo", event.target.files[0]);
    setUploadStatus("Procesando PDF, OCR, tablas y seguridad…");
    try { const result = await request<any>("/uploads/pdf", { method: "POST", body }); setUploadStatus(`${result.nombre}: ${result.fragmentos} fragmentos, ${result.tablas_indexadas} tablas indexadas${result.resumen_alertas ? ` · ${result.resumen_alertas}` : ""}`); }
    catch (err) { setUploadStatus(err instanceof Error ? err.message : "No se pudo procesar el PDF."); }
    event.target.value = "";
  }

  async function generate(kind: "flashcards" | "examenes") {
    if (!user || !input.trim()) { setError("Escribe un tema en el cuadro de chat."); return; }
    try {
      const result = await request<any>(`/${kind}/generate`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ usuario_id: user.usuario_id, texto_fuente: input, tema: input, idioma: language, n: 5 }) });
      if (kind === "flashcards") setCards(result.flashcards ?? []); else setQuestions(result.preguntas ?? []);
      setError(result.diagnostico ?? "Material generado.");
    } catch (err) { setError(err instanceof Error ? err.message : "No se pudo generar material."); }
  }

  if (!user) return <main className="flex min-h-screen items-center justify-center bg-slate-950 p-6 text-slate-100"><form onSubmit={authenticate} className="w-full max-w-md space-y-4 rounded-2xl border border-slate-800 bg-slate-900 p-6"><h1 className="text-2xl font-bold text-cyan-300">Medicine Study AI</h1><input required minLength={3} placeholder="Usuario" value={auth.usuario} onChange={(e) => setAuth({ ...auth, usuario: e.target.value })} className="w-full rounded-lg bg-slate-950 p-3" /><input required minLength={4} type="password" placeholder="Contraseña" value={auth.password} onChange={(e) => setAuth({ ...auth, password: e.target.value })} className="w-full rounded-lg bg-slate-950 p-3" /><button className="w-full rounded-lg bg-cyan-600 p-3 font-semibold">{authMode === "login" ? "Iniciar sesión" : "Crear cuenta"}</button><button type="button" onClick={() => setAuthMode(authMode === "login" ? "register" : "login")} className="w-full text-sm text-cyan-300">{authMode === "login" ? "Necesito crear una cuenta" : "Ya tengo una cuenta"}</button>{error && <p className="text-sm text-amber-300">{error}</p>}</form></main>;

  const nav = ["chat", "evidencia", "calculadoras", "interacciones", "flashcards", "examen", "progreso", "auditoria"];
  return <main className={settings.dark ? "min-h-screen bg-slate-950 text-slate-100" : "min-h-screen bg-slate-100 text-slate-900"}><header className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 bg-slate-900 px-6 py-4"><div><h1 className="text-xl font-bold text-cyan-300">Medicine Study AI</h1><p className="text-xs text-slate-400">👤 {user.usuario} · {language}</p></div><div className="flex flex-wrap gap-2"><label className="cursor-pointer rounded-lg bg-slate-800 px-3 py-2 text-sm">Cargar PDF<input type="file" accept=".pdf,application/pdf" onChange={upload} className="hidden" /></label><button onClick={() => { localStorage.removeItem("msai-user"); setUser(null); }} className="rounded-lg border border-slate-700 px-3 py-2 text-sm">Salir</button></div></header>
    <div className="flex min-h-[calc(100vh-73px)] flex-col lg:flex-row"><aside className="w-full space-y-3 border-r border-slate-800 bg-slate-900 p-4 lg:w-72"><button onClick={resetChat} className="w-full rounded-lg bg-cyan-800 p-2 text-sm">＋ Nuevo chat</button><label className="text-xs text-slate-400">Idioma<select value={language} onChange={(e) => setLanguage(e.target.value)} className="mt-1 w-full rounded bg-slate-950 p-2">{(options?.idiomas ?? [{ codigo: "es", nombre: "Español" }]).map((item) => <option key={item.codigo} value={item.codigo}>{item.nombre}</option>)}</select></label><label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={settings.pubmed} onChange={(e) => setSettings({ ...settings, pubmed: e.target.checked })} /> Búsqueda PubMed</label><label className="text-xs text-slate-400">Nivel de evidencia<select value={settings.evidence} onChange={(e) => setSettings({ ...settings, evidence: e.target.value })} className="mt-1 w-full rounded bg-slate-950 p-2">{(options?.modos_evidencia ?? ["todo"]).map((item) => <option key={item} value={item}>{item}</option>)}</select></label><label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={settings.factuality} onChange={(e) => setSettings({ ...settings, factuality: e.target.checked })} /> Verificar factualidad</label><label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={settings.dark} onChange={(e) => setSettings({ ...settings, dark: e.target.checked })} /> Tema oscuro</label><div className="border-t border-slate-800 pt-3"><p className="mb-2 text-xs font-bold text-slate-400">Historial</p>{chats.map((chat) => <div key={chat.id} className="mb-1 flex gap-1"><button onClick={() => loadChat(chat.id)} className="min-w-0 flex-1 truncate rounded bg-slate-800 p-2 text-left text-xs">{chat.titulo}</button><button onClick={() => deleteChat(chat.id)} className="rounded bg-red-950 px-2 text-xs">×</button></div>)}</div><div className="border-t border-slate-800 pt-3 text-xs text-slate-400">{uploadStatus || "PDF: OCR, extracción de tablas y RAG disponibles."}</div></aside>
      <section className="flex-1"><nav className="flex gap-2 overflow-x-auto border-b border-slate-800 bg-slate-900 px-4 py-3">{nav.map((item) => <button key={item} onClick={() => setSection(item)} className={`rounded-lg px-3 py-2 text-sm ${section === item ? "bg-cyan-700" : "bg-slate-800"}`}>{item[0].toUpperCase() + item.slice(1)}</button>)}</nav><div className="mx-auto max-w-7xl p-4">{section === "chat" && <ChatView messages={messages} input={input} setInput={setInput} send={send} busy={busy} error={error} papers={papers} sources={sources} process={process} factuality={factuality} contradictions={contradictions} icd={icd} onFeedback={async (message: Message, value: number) => { if (!user) return; await request("/feedback", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ usuario_id: user.usuario_id, chat_id: chatId, pregunta: message.question ?? "", respuesta: message.content, valoracion: value, fuentes: sources, idioma: language }) }); }} />}{section === "evidencia" && <Evidence userId={user.usuario_id} language={language} mode={settings.evidence} papers={papers} setPapers={setPapers} />}{section === "calculadoras" && <Calculator />}{section === "interacciones" && <Interactions language={language} />}{section === "flashcards" && <Material title="Flashcards" items={cards} flashcards userId={user.usuario_id} onGenerate={() => generate("flashcards")} />}{section === "examen" && <Material title="Examen" items={questions} userId={user.usuario_id} onGenerate={() => generate("examenes")} />}{section === "progreso" && <Progress data={progress} />}{section === "auditoria" && <Audit userId={user.usuario_id} />}</div></section></div></main>;
}

function ChatView({ messages, input, setInput, send, busy, error, papers, sources, process, factuality, contradictions, icd, onFeedback }: any) {
  return <section className="grid gap-4 xl:grid-cols-[1fr_360px]"><div className="flex min-h-[75vh] flex-col rounded-2xl border border-slate-800 bg-slate-900/70 p-4"><div className="flex-1 space-y-4 overflow-y-auto">{messages.length === 0 && <div className="mx-auto max-w-xl py-20 text-center text-slate-400"><h2 className="text-2xl font-bold text-cyan-300">Medicine Study AI</h2><p className="mt-3">Consulta temas médicos, activa evidencia PubMed o carga tus PDFs.</p></div>}{messages.map((message: Message, index: number) => <article key={index} className={`max-w-4xl rounded-2xl p-4 ${message.role === "user" ? "ml-auto bg-cyan-950" : "bg-slate-800"}`}>{message.role === "assistant" ? <><ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[rehypeKatex]}>{message.content || "Generando respuesta…"}</ReactMarkdown>{message.content && <div className="mt-3 flex gap-2"><button onClick={() => onFeedback(message, 1)} className="text-xs text-slate-400">👍 Útil</button><button onClick={() => onFeedback(message, -1)} className="text-xs text-slate-400">👎 No útil</button></div>}</> : <p className="whitespace-pre-wrap">{message.content}</p>}</article>)}</div>{error && <p className="my-3 rounded-lg bg-amber-950 p-3 text-sm text-amber-200">{error}</p>}<form onSubmit={send} className="mt-4 flex gap-2"><textarea value={input} onChange={(e) => setInput(e.target.value)} disabled={busy} rows={3} placeholder="Pregunta médica o escribe un tema para materiales…" className="min-w-0 flex-1 rounded-xl bg-slate-950 p-3" /><button className="rounded-xl bg-cyan-600 px-5" disabled={busy}>Enviar</button></form></div><aside className="space-y-3"><Panel title="Proceso">{process.length ? process.map((item: string) => <p key={item} className="text-xs text-slate-400">✓ {item}</p>) : <p className="text-xs text-slate-500">Los pasos del turno aparecerán aquí.</p>}{factuality && <pre className="mt-2 whitespace-pre-wrap text-xs">{JSON.stringify(factuality, null, 2)}</pre>}{contradictions.length > 0 && <p className="text-xs text-amber-300">⚠ Contradicciones fisiológicas detectadas.</p>}{icd && <p className="text-xs text-cyan-300">ICD-11: {icd.terminos_encontrados?.length ?? 0} términos.</p>}</Panel><Panel title="Fuentes">{(sources.length ? sources : papers).map((paper: any, index: number) => <div key={index} className="border-t border-slate-800 py-2 text-xs"><b>{paper.titulo ?? paper.fuente}</b><p className="text-slate-400">{paper.resumen ?? paper.texto}</p></div>)}</Panel></aside></section>;
}

function Panel({ title, children }: { title: string; children: ReactNode }) { return <div className="rounded-2xl border border-slate-800 bg-slate-900 p-4"><h2 className="mb-3 font-semibold text-cyan-300">{title}</h2>{children}</div>; }

function Evidence({ userId, language, mode, papers, setPapers }: any) {
  const [query, setQuery] = useState(""); const [busy, setBusy] = useState(false); const [debug, setDebug] = useState<string[]>([]);
  async function search(event: FormEvent) { event.preventDefault(); setBusy(true); try { const result = await request<any>("/search/pubmed", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ usuario_id: userId, consulta: query, idioma: language, modo_evidencia: mode }) }); setPapers(result.papers ?? []); setDebug(result.debug ?? []); } catch (err) { setDebug([err instanceof Error ? err.message : "Error"]); } finally { setBusy(false); } }
  return <section className="space-y-4"><Panel title="PubMed, Europe PMC y evidencia"><form onSubmit={search} className="flex gap-2"><input required minLength={2} value={query} onChange={(e) => setQuery(e.target.value)} className="flex-1 rounded bg-slate-950 p-3" placeholder="Consulta científica" /><button disabled={busy} className="rounded bg-cyan-700 px-4">Buscar</button></form>{debug.map((item) => <p key={item} className="text-xs text-slate-500">{item}</p>)}</Panel><div className="grid gap-3 md:grid-cols-2">{papers.map((paper: Paper, index: number) => <article key={index} className="rounded-xl bg-slate-900 p-4"><h3 className="font-semibold">{paper.titulo}</h3><p className="mt-2 text-sm text-slate-400">{paper.resumen}</p><p className="mt-2 text-xs text-cyan-300">{paper.pmid ? `PMID: ${paper.pmid}` : paper.doi} · {paper.revista} · {paper.anio}</p></article>)}</div></section>;
}

function Calculator() {
  const [operation, setOperation] = useState("imc"); const [params, setParams] = useState<Record<string, string>>({ peso_kg: "70", altura_cm: "175", edad: "40", creatinina_mg_dl: "1", sexo: "M", mg_por_kg: "10", farmaco: "vancomicina", aclaramiento_ml_min: "45" }); const [result, setResult] = useState<any>(null); const fields = useMemo(() => ({ imc: ["peso_kg", "altura_cm"], superficie_corporal: ["peso_kg", "altura_cm", "formula"], aclaramiento_creatinina: ["edad", "peso_kg", "altura_cm", "creatinina_mg_dl", "sexo"], egfr: ["edad", "creatinina_mg_dl", "sexo"], dosis_por_peso: ["peso_kg", "mg_por_kg", "dosis_max_mg", "dosis_min_mg", "tomas_por_dia"], ajuste_renal: ["farmaco", "aclaramiento_ml_min"] }[operation] ?? []), [operation]);
  async function calculate() { try { setResult(await request("/calculadoras", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ operacion: operation, parametros: params }) })); } catch (err) { setResult({ error: err instanceof Error ? err.message : "Error" }); } }
  return <Panel title="Calculadoras clínicas"><select value={operation} onChange={(e) => setOperation(e.target.value)} className="w-full rounded bg-slate-950 p-3">{["imc", "superficie_corporal", "aclaramiento_creatinina", "egfr", "dosis_por_peso", "ajuste_renal"].map((item) => <option key={item}>{item}</option>)}</select><div className="mt-3 grid gap-3 sm:grid-cols-2">{fields.map((key) => <input key={key} value={params[key] ?? ""} onChange={(e) => setParams({ ...params, [key]: e.target.value })} placeholder={key} className="rounded bg-slate-950 p-3" />)}</div><button onClick={calculate} className="mt-4 rounded bg-cyan-700 px-4 py-2">Calcular</button>{result && <pre className="mt-4 whitespace-pre-wrap rounded bg-slate-950 p-3 text-sm">{JSON.stringify(result, null, 2)}</pre>}</Panel>;
}

function Interactions({ language }: { language: string }) {
  const [value, setValue] = useState("warfarina\nibuprofeno"); const [result, setResult] = useState<any>(null);
  async function check() { const result = await request<any>("/interacciones", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ farmacos: value.split("\n").map((item) => item.trim()).filter(Boolean), idioma: language }) }); setResult(result); }
  return <Panel title="Interacciones farmacológicas"><textarea rows={5} value={value} onChange={(e) => setValue(e.target.value)} className="w-full rounded bg-slate-950 p-3" /><button onClick={check} className="mt-3 rounded bg-cyan-700 px-4 py-2">Verificar interacciones</button>{result && <pre className="mt-4 whitespace-pre-wrap text-sm">{JSON.stringify(result, null, 2)}</pre>}</Panel>;
}

function Material({ title, items, onGenerate, flashcards = false, userId }: any) { const [revealed, setRevealed] = useState<Record<number, boolean>>({}); return <Panel title={title}><button onClick={onGenerate} className="rounded bg-cyan-700 px-4 py-2">Generar desde el tema del chat</button><div className="mt-4 grid gap-3 md:grid-cols-2">{items.map((item: any, index: number) => <article key={index} className="rounded-xl bg-slate-800 p-4"><b>{item.pregunta}</b>{flashcards ? <><button onClick={() => setRevealed({ ...revealed, [index]: true })} className="mt-3 block rounded bg-slate-700 px-3 py-2 text-sm">Mostrar respuesta</button>{revealed[index] && <><p className="mt-2">{item.respuesta}</p><div className="mt-3 flex gap-2">{["otra_vez", "dificil", "bien", "facil"].map((button) => <button key={button} onClick={() => request("/flashcards/review", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ usuario_id: userId, flashcard_id: item.id, boton: button }) })} className="rounded bg-cyan-900 px-2 py-1 text-xs">{button}</button>)}</div></>} </> : <>{item.opciones?.map((option: string, optionIndex: number) => <button key={optionIndex} onClick={() => request("/examenes/attempt", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ usuario_id: userId, pregunta_id: item.id, correcta: optionIndex === item.respuesta_correcta }) })} className="mt-2 block w-full rounded bg-slate-700 p-2 text-left text-sm">{option}</button>)}<p className="mt-2 text-slate-300">{item.explicacion}</p></>}</article>)}</div></Panel>; }
function Progress({ data }: { data: any }) {
  const chartData = (data?.temas ?? []).map((item: any) => ({ tema: item.tema, porcentaje: Math.round((item.porcentaje ?? 0) * 100) }));
  return <Panel title="Mi progreso"><div className="grid gap-4 md:grid-cols-2"><div><p className="mb-2 text-sm text-slate-400">Resumen de actividad</p><pre className="whitespace-pre-wrap text-sm">{JSON.stringify(data?.resumen ?? {}, null, 2)}</pre></div><div className="h-64">{chartData.length ? <ResponsiveContainer width="100%" height="100%"><BarChart data={chartData}><CartesianGrid strokeDasharray="3 3" stroke="#334155" /><XAxis dataKey="tema" tick={{ fill: "#94a3b8", fontSize: 10 }} /><YAxis domain={[0, 100]} tick={{ fill: "#94a3b8", fontSize: 10 }} /><Tooltip /><Bar dataKey="porcentaje" fill="#22d3ee" /></BarChart></ResponsiveContainer> : <p className="text-sm text-slate-500">Completa exámenes para ver tu progreso por tema.</p>}</div></div><pre className="mt-4 whitespace-pre-wrap text-sm">{JSON.stringify(data?.temas ?? [], null, 2)}</pre></Panel>;
}
function Audit({ userId }: { userId: number }) { const [data, setData] = useState<any[]>([]); useEffect(() => { request<any[]>(`/auditoria?usuario_id=${userId}`).then(setData).catch(() => {}); }, [userId]); return <Panel title="Auditoría de uso"><pre className="whitespace-pre-wrap text-sm">{JSON.stringify(data, null, 2)}</pre></Panel>; }

export default App;
