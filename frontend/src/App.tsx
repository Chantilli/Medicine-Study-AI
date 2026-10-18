import { ChangeEvent, FormEvent, useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";

type Message = { role: "user" | "assistant"; content: string };
type Paper = { titulo?: string; resumen?: string; pmid?: string; doi?: string };
type User = { usuario_id: number; usuario: string };
const API = "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, init);
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail ?? "La operación no se pudo completar.");
  return data;
}

export default function App() {
  const [user, setUser] = useState<User | null>(() => JSON.parse(localStorage.getItem("msai-user") ?? "null"));
  const [authMode, setAuthMode] = useState<"login" | "register">("login");
  const [auth, setAuth] = useState({ usuario: "", password: "" });
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [papers, setPapers] = useState<Paper[]>([]);
  const [section, setSection] = useState("chat");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [cards, setCards] = useState<any[]>([]);
  const [questions, setQuestions] = useState<any[]>([]);
  const [progress, setProgress] = useState<any>(null);

  useEffect(() => {
    if (!user) return;
    request<any>(`/flashcards?usuario_id=${user.usuario_id}&pendientes=true`).then((data) => setCards(data.flashcards)).catch(() => {});
    request<any>(`/progreso?usuario_id=${user.usuario_id}`).then(setProgress).catch(() => {});
  }, [user]);

  async function authenticate(event: FormEvent) {
    event.preventDefault();
    try {
      const result = await request<User>(`/auth/${authMode === "login" ? "login" : "register"}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(auth) });
      localStorage.setItem("msai-user", JSON.stringify(result));
      setUser(result);
      setError("");
    } catch (err) { setError(err instanceof Error ? err.message : "No se pudo iniciar sesión."); }
  }

  async function send(event: FormEvent) {
    event.preventDefault();
    const text = input.trim();
    if (!text || busy) return;
    setInput(""); setBusy(true); setError("");
    setMessages((current) => [...current, { role: "user", content: text }, { role: "assistant", content: "" }]);
    try {
      const response = await fetch(`${API}/chat/stream`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ mensaje: text, usuario_id: user?.usuario_id, historial: messages, buscar_evidencia: true }) });
      if (!response.body) throw new Error("El navegador no soporta streaming.");
      const reader = response.body.getReader(); const decoder = new TextDecoder(); let buffer = "";
      while (true) {
        const { value, done } = await reader.read(); if (done) break;
        buffer += decoder.decode(value, { stream: true }); const chunks = buffer.split("\n\n"); buffer = chunks.pop() ?? "";
        for (const chunk of chunks) {
          const eventName = chunk.match(/^event: (.+)$/m)?.[1]; const raw = chunk.match(/^data: (.+)$/m)?.[1]; if (!raw) continue;
          const data = JSON.parse(raw);
          if (eventName === "token" || eventName === "emergency") setMessages((current) => { const next = [...current]; next[next.length - 1] = { role: "assistant", content: next[next.length - 1].content + data.content }; return next; });
          if (eventName === "evidence") setPapers(data.papers ?? []);
          if (eventName === "error" || eventName === "warning") setError(data.message);
        }
      }
    } catch (err) { setError(err instanceof Error ? err.message : "No se pudo enviar la consulta."); } finally { setBusy(false); }
  }

  async function upload(event: ChangeEvent<HTMLInputElement>) {
    if (!user || !event.target.files?.[0]) return;
    const body = new FormData(); body.append("usuario_id", String(user.usuario_id)); body.append("archivo", event.target.files[0]);
    try { await request("/uploads/pdf", { method: "POST", body }); setError("PDF procesado e indexado para tus consultas."); } catch (err) { setError(err instanceof Error ? err.message : "No se pudo procesar el PDF."); }
  }

  async function generate(kind: "flashcards" | "examenes") {
    if (!user || !input.trim()) { setError("Escribe primero un tema o texto fuente en el chat."); return; }
    try {
      const result = await request<any>(`/${kind}/generate`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ usuario_id: user.usuario_id, texto_fuente: input, n: 5 }) });
      if (kind === "flashcards") setCards(result.flashcards ?? []); else setQuestions(result.preguntas ?? []);
      setError(result.diagnostico ?? "Material generado y guardado.");
    } catch (err) { setError(err instanceof Error ? err.message : "No se pudo generar material."); }
  }

  if (!user) return <main className="flex min-h-screen items-center justify-center bg-slate-950 p-6 text-slate-100"><form onSubmit={authenticate} className="w-full max-w-md space-y-4 rounded-2xl border border-slate-800 bg-slate-900 p-6"><h1 className="text-2xl font-bold text-cyan-300">Medicine Study AI</h1><input required placeholder="Usuario" value={auth.usuario} onChange={(e) => setAuth({ ...auth, usuario: e.target.value })} className="w-full rounded-lg bg-slate-950 p-3" /><input required type="password" placeholder="Contraseña" value={auth.password} onChange={(e) => setAuth({ ...auth, password: e.target.value })} className="w-full rounded-lg bg-slate-950 p-3" /><button className="w-full rounded-lg bg-cyan-600 p-3 font-semibold">{authMode === "login" ? "Iniciar sesión" : "Crear cuenta"}</button><button type="button" onClick={() => setAuthMode(authMode === "login" ? "register" : "login")} className="w-full text-sm text-cyan-300">{authMode === "login" ? "Necesito crear una cuenta" : "Ya tengo una cuenta"}</button>{error && <p className="text-sm text-amber-300">{error}</p>}</form></main>;

  return <main className="min-h-screen bg-slate-950 text-slate-100"><header className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 bg-slate-900 px-6 py-4"><div><h1 className="text-xl font-bold text-cyan-300">Medicine Study AI</h1><p className="text-xs text-slate-400">Sesión: {user.usuario}</p></div><div className="flex gap-2"><label className="cursor-pointer rounded-lg bg-slate-800 px-3 py-2 text-sm">Subir PDF<input type="file" accept=".pdf,application/pdf" onChange={upload} className="hidden" /></label><button onClick={() => { localStorage.removeItem("msai-user"); setUser(null); }} className="rounded-lg border border-slate-700 px-3 py-2 text-sm">Salir</button></div></header>
    <nav className="flex gap-2 overflow-x-auto border-b border-slate-800 px-6 py-3">{["chat", "calculadoras", "flashcards", "examen", "progreso"].map((item) => <button key={item} onClick={() => setSection(item)} className={`rounded-lg px-3 py-2 text-sm ${section === item ? "bg-cyan-700" : "bg-slate-900"}`}>{item[0].toUpperCase() + item.slice(1)}</button>)}</nav>
    <div className="mx-auto max-w-7xl p-6">{section === "chat" && <section className="grid gap-6 lg:grid-cols-[1fr_340px]"><div className="flex min-h-[70vh] flex-col rounded-2xl border border-slate-800 bg-slate-900/60 p-4"><div className="flex-1 space-y-4 overflow-y-auto">{messages.map((message, index) => <article key={index} className={`max-w-3xl rounded-2xl p-4 ${message.role === "user" ? "ml-auto bg-cyan-950" : "bg-slate-800"}`}>{message.role === "assistant" ? <ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[rehypeKatex]}>{message.content || "Generando respuesta…"}</ReactMarkdown> : message.content}</article>)}</div>{error && <p className="my-3 rounded-lg bg-amber-950 p-3 text-sm text-amber-200">{error}</p>}<form onSubmit={send} className="mt-4 flex gap-2"><input value={input} onChange={(e) => setInput(e.target.value)} disabled={busy} placeholder="Pregunta o escribe un tema fuente…" className="min-w-0 flex-1 rounded-xl bg-slate-950 p-3" /><button className="rounded-xl bg-cyan-600 px-5" disabled={busy}>Enviar</button></form></div><aside className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4"><h2 className="font-semibold">Fuentes</h2>{papers.map((paper, index) => <div key={index} className="border-t border-slate-800 py-3 text-sm"><b>{paper.titulo}</b><p className="text-xs text-slate-400">{paper.resumen}</p></div>)}</aside></section>}
      {section === "calculadoras" && <Calculator userId={user.usuario_id} />}
      {section === "flashcards" && <Material title="Flashcards" items={cards} onGenerate={() => generate("flashcards")} flashcards userId={user.usuario_id} />}
      {section === "examen" && <Material title="Examen" items={questions} onGenerate={() => generate("examenes")} userId={user.usuario_id} />}
      {section === "progreso" && <section className="rounded-2xl border border-slate-800 bg-slate-900 p-6"><h2 className="text-xl font-semibold">Progreso</h2><pre className="mt-4 whitespace-pre-wrap text-sm text-slate-300">{JSON.stringify(progress, null, 2)}</pre></section>}</div></main>;
}

function Material({ title, items, onGenerate, flashcards = false, userId }: { title: string; items: any[]; onGenerate: () => void; flashcards?: boolean; userId: number }) {
  const [revealed, setRevealed] = useState<Record<number, boolean>>({});
  async function review(item: any, button: string) {
    await request("/flashcards/review", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ usuario_id: userId, flashcard_id: item.id, boton: button }) });
  }
  return <section className="rounded-2xl border border-slate-800 bg-slate-900 p-6"><div className="flex items-center justify-between"><h2 className="text-xl font-semibold">{title}</h2><button onClick={onGenerate} className="rounded-lg bg-cyan-700 px-4 py-2">Generar desde el tema del chat</button></div><div className="mt-6 grid gap-3 md:grid-cols-2">{items.map((item, index) => <div key={index} className="rounded-xl bg-slate-800 p-4"><b>{item.pregunta}</b>{flashcards ? <><button onClick={() => setRevealed({ ...revealed, [index]: true })} className="mt-3 block rounded bg-slate-700 px-3 py-2 text-sm">Mostrar respuesta</button>{revealed[index] && <><p className="mt-2 text-slate-300">{item.respuesta}</p><div className="mt-3 flex flex-wrap gap-2">{["otra_vez", "dificil", "bien", "facil"].map((button) => <button key={button} onClick={() => review(item, button)} className="rounded bg-cyan-900 px-2 py-1 text-xs">{button}</button>)}</div></>} </> : <>{item.opciones?.map((option: string, optionIndex: number) => <button key={optionIndex} onClick={() => request("/examenes/attempt", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ usuario_id: userId, pregunta_id: item.id, correcta: optionIndex === item.respuesta_correcta }) })} className="mt-2 block w-full rounded bg-slate-700 p-2 text-left text-sm">{option}</button>)}<p className="mt-2 text-slate-300">{item.explicacion}</p></>}</div>)}</div></section>;
}

function Calculator({ userId }: { userId: number }) {
  const [operation, setOperation] = useState("imc"); const [params, setParams] = useState({ peso_kg: "70", altura_cm: "175" }); const [result, setResult] = useState<any>(null);
  async function calculate() { setResult(await request(`/calculadoras`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ operacion: operation, parametros: { ...params, usuario_id: userId } }) })); }
  return <section className="max-w-xl rounded-2xl border border-slate-800 bg-slate-900 p-6"><h2 className="text-xl font-semibold">Calculadoras clínicas</h2><select value={operation} onChange={(e) => setOperation(e.target.value)} className="mt-4 w-full rounded-lg bg-slate-950 p-3"><option value="imc">IMC</option><option value="superficie_corporal">Superficie corporal</option><option value="egfr">eGFR CKD-EPI</option><option value="dosis_por_peso">Dosis por peso</option><option value="ajuste_renal">Ajuste renal</option></select><div className="mt-3 grid gap-3 sm:grid-cols-2">{Object.entries(params).map(([key, value]) => <input key={key} value={value} onChange={(e) => setParams({ ...params, [key]: e.target.value })} placeholder={key} className="rounded-lg bg-slate-950 p-3" />)}</div><button onClick={calculate} className="mt-4 rounded-lg bg-cyan-700 px-4 py-2">Calcular</button>{result && <pre className="mt-4 whitespace-pre-wrap rounded-lg bg-slate-950 p-3">{JSON.stringify(result, null, 2)}</pre>}</section>;
}
