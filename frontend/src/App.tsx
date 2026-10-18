import { FormEvent, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";

type Message = { role: "user" | "assistant"; content: string };
type Paper = { titulo?: string; resumen?: string; pmid?: string; doi?: string };

const API = "/api";

export default function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [papers, setPapers] = useState<Paper[]>([]);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState("");

  async function send(event: FormEvent) {
    event.preventDefault();
    const text = input.trim();
    if (!text || busy) return;
    setInput("");
    setError("");
    setBusy(true);
    setProgress(5);
    setMessages((current) => [...current, { role: "user", content: text }, { role: "assistant", content: "" }]);
    try {
      const response = await fetch(`${API}/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mensaje: text, historial: messages, buscar_evidencia: true }),
      });
      if (!response.body) throw new Error("El navegador no soporta streaming.");
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const chunks = buffer.split("\n\n");
        buffer = chunks.pop() ?? "";
        for (const chunk of chunks) {
          const eventName = chunk.match(/^event: (.+)$/m)?.[1];
          const raw = chunk.match(/^data: (.+)$/m)?.[1];
          if (!raw) continue;
          const data = JSON.parse(raw);
          if (eventName === "token") {
            setProgress((value) => Math.min(95, value + 2));
            setMessages((current) => {
              const next = [...current];
              next[next.length - 1] = { role: "assistant", content: next[next.length - 1].content + data.content };
              return next;
            });
          } else if (eventName === "evidence") setPapers(data.papers ?? []);
          else if (eventName === "warning") setError(data.message);
          else if (eventName === "error") setError(data.message);
          else if (eventName === "emergency") setMessages((current) => {
            const next = [...current];
            next[next.length - 1] = { role: "assistant", content: data.content };
            return next;
          });
        }
      }
      setProgress(100);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo enviar la consulta.");
    } finally {
      setBusy(false);
    }
  }

  return <main className="min-h-screen text-slate-100">
    <header className="border-b border-slate-800 bg-slate-900/80 px-6 py-4">
      <div className="mx-auto flex max-w-7xl items-center justify-between">
        <div><h1 className="text-xl font-bold text-cyan-300">Medicine Study AI</h1><p className="text-xs text-slate-400">Evidencia médica para estudiar mejor</p></div>
        <span className="rounded-full border border-cyan-800 px-3 py-1 text-xs text-cyan-300">FastAPI + React</span>
      </div>
    </header>
    <div className="mx-auto grid max-w-7xl gap-6 p-6 lg:grid-cols-[1fr_340px]">
      <section className="flex min-h-[calc(100vh-130px)] flex-col rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
        <div className="flex-1 space-y-4 overflow-y-auto pr-2">
          {messages.length === 0 && <div className="mx-auto mt-24 max-w-lg text-center"><h2 className="text-3xl font-semibold">¿Qué quieres estudiar hoy?</h2><p className="mt-3 text-slate-400">Pregunta sobre fisiología, farmacología o revisa evidencia de PubMed. Las respuestas son educativas.</p></div>}
          {messages.map((message, index) => <article key={index} className={message.role === "user" ? "ml-auto max-w-2xl rounded-2xl bg-cyan-950 p-4" : "max-w-3xl rounded-2xl bg-slate-800 p-4"}>
            {message.role === "assistant" ? <ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[rehypeKatex]}>{message.content || "Generando respuesta…"}</ReactMarkdown> : <p className="whitespace-pre-wrap">{message.content}</p>}
          </article>)}
        </div>
        {error && <p className="my-3 rounded-lg border border-amber-700 bg-amber-950/40 p-3 text-sm text-amber-200">{error}</p>}
        <form onSubmit={send} className="mt-4 flex gap-2">
          <input value={input} onChange={(event) => setInput(event.target.value)} disabled={busy} placeholder="Escribe una pregunta médica…" className="min-w-0 flex-1 rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 outline-none focus:border-cyan-500" />
          <button disabled={busy || !input.trim()} className="rounded-xl bg-cyan-600 px-5 py-3 font-semibold text-white transition hover:bg-cyan-500 disabled:cursor-not-allowed disabled:opacity-50">{busy ? "…" : "Enviar"}</button>
        </form>
      </section>
      <aside className="space-y-4">
        <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4"><h2 className="font-semibold">Progreso</h2><div className="mt-3 h-2 rounded bg-slate-700"><div className="h-2 rounded bg-cyan-400 transition-all" style={{ width: `${progress}%` }} /></div><p className="mt-2 text-xs text-slate-400">Vista preparada para conectar Recharts con métricas de estudio.</p></section>
        <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4"><h2 className="font-semibold">Fuentes recuperadas</h2>{papers.length === 0 ? <p className="mt-2 text-sm text-slate-400">Las fuentes aparecerán aquí durante la búsqueda.</p> : <div className="mt-3 space-y-3">{papers.map((paper, index) => <div key={index} className="border-t border-slate-800 pt-3 text-sm"><p className="font-medium text-cyan-200">{paper.titulo}</p><p className="mt-1 line-clamp-3 text-xs text-slate-400">{paper.resumen}</p><p className="mt-1 text-[11px] text-slate-500">{paper.pmid ? `PMID: ${paper.pmid}` : paper.doi}</p></div>)}</div>}</section>
      </aside>
    </div>
  </main>;
}
