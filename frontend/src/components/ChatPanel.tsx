import type { FormEvent } from "react";

type ChatMessage = {
  id: number;
  role: "user" | "assistant";
  text: string;
  hint?: string;
};

type ChatPanelProps = {
  messages: ChatMessage[];
  query: string;
  isLoading: boolean;
  quickPrompts: string[];
  onQuickPrompt: (prompt: string) => void;
  onQueryChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
};

export default function ChatPanel({
  messages,
  query,
  isLoading,
  quickPrompts,
  onQuickPrompt,
  onQueryChange,
  onSubmit,
}: ChatPanelProps) {
  return (
    <>
      <div className="mb-4 rounded-xl border border-slate-200 bg-slate-50/80 p-3">
        <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-600">
          Quick Prompts
        </p>
        <div className="mt-2 flex flex-wrap gap-2">
          {quickPrompts.map((prompt) => (
            <button
              key={prompt}
              type="button"
              onClick={() => onQuickPrompt(prompt)}
              className="rounded-full border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:border-emerald-400 hover:text-emerald-800"
              disabled={isLoading}
            >
              {prompt}
            </button>
          ))}
        </div>
      </div>

      <div className="h-[430px] overflow-y-auto rounded-xl border border-slate-100 bg-slate-50/60 p-3">
        <div className="space-y-3">
          {messages.map((message) => {
            const isAssistant = message.role === "assistant";
            return (
              <div
                key={message.id}
                className={`max-w-[92%] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm ${
                  isAssistant
                    ? "border border-emerald-200 bg-emerald-50/70 text-slate-800"
                    : "ml-auto border border-slate-300 bg-white text-slate-900"
                }`}
              >
                <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                  {isAssistant ? "Agent" : "You"}
                </p>
                <p className="mt-1 whitespace-pre-wrap">{message.text}</p>
                {message.hint ? (
                  <p className="mt-2 rounded-lg border border-slate-200 bg-white/80 px-2 py-1 text-xs text-slate-600">
                    {message.hint}
                  </p>
                ) : null}
              </div>
            );
          })}
        </div>
      </div>

      <form onSubmit={onSubmit} className="mt-4 space-y-3">
        <div className="flex gap-2">
          <input
            type="text"
            value={query}
            onChange={(event) => onQueryChange(event.target.value)}
            placeholder="Ask for forecast, risk, simulate, or disease context..."
            className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-900 shadow-sm outline-none focus:border-emerald-500"
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={isLoading}
            className="rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isLoading ? "Working..." : "Send"}
          </button>
        </div>
      </form>
    </>
  );
}
