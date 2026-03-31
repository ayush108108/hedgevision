import React, { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { CheckCircle2, ChevronLeft, ChevronRight, Copy, Sparkles } from "lucide-react";
import { useBYOKStore } from "../state/byokStore";
import { useOnboardingStore } from "../state/onboardingStore";

const TOTAL_STEPS = 5;

function StepBadge({ current }: { current: number }) {
  return (
    <div className="flex items-center gap-2 text-sm text-slate-300">
      {Array.from({ length: TOTAL_STEPS }).map((_, idx) => {
        const step = idx + 1;
        const active = step === current;
        const done = step < current;
        return (
          <div
            key={step}
            className={`h-8 w-8 rounded-full flex items-center justify-center border ${
              active
                ? "bg-blue-500/30 border-blue-400 text-blue-200"
                : done
                  ? "bg-emerald-500/30 border-emerald-400 text-emerald-200"
                  : "bg-slate-800 border-slate-600 text-slate-400"
            }`}
          >
            {done ? <CheckCircle2 size={16} /> : step}
          </div>
        );
      })}
    </div>
  );
}

export function OnboardingPage() {
  const navigate = useNavigate();
  const byok = useBYOKStore();
  const wizard = useOnboardingStore();
  const [copied, setCopied] = useState(false);

  const envSnippet = useMemo(() => {
    const provider = wizard.modelRuntime;
    const lines = [
      `DATA_BACKEND=${wizard.dataBackend}`,
      "DB_PATH=backend/prices.db",
      `LLM_PROVIDER=${provider}`,
      `LLM_MODEL=${wizard.modelName || "llama3.2"}`,
      `ENABLE_EXTERNAL_LLM=false`,
      `OLLAMA_BASE_URL=${wizard.ollamaBaseUrl}`,
      `LOCAL_ML_BACKEND=${wizard.cpuBackend}`,
      `LOCAL_ML_MODEL_PATH=${wizard.cpuModelPath}`,
      `BROKER_BACKEND=${wizard.brokerBackend}`,
      `CCXT_EXCHANGE=${wizard.ccxtExchange}`,
    ];
    return lines.join("\n");
  }, [wizard]);

  const goNext = () => wizard.setStep(Math.min(TOTAL_STEPS, wizard.step + 1));
  const goPrev = () => wizard.setStep(Math.max(1, wizard.step - 1));

  const applyToUI = () => {
    byok.setProvider(wizard.modelRuntime === "cpu" ? "cpu" : wizard.modelRuntime);
    byok.setModel(wizard.modelName || "llama3.2");
    byok.setUseLlm(wizard.modelRuntime !== "rules");
  };

  const finish = () => {
    applyToUI();
    wizard.markCompleted(true);
    navigate("/signals");
  };

  const copySnippet = async () => {
    try {
      await navigator.clipboard.writeText(envSnippet);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-blue-950 text-white">
      <div className="max-w-5xl mx-auto px-6 py-10">
        <div className="rounded-2xl border border-white/10 bg-slate-900/70 p-6 mb-6">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div>
              <h1 className="text-3xl font-bold flex items-center gap-2">
                <Sparkles className="text-cyan-300" /> Onboarding Wizard
              </h1>
              <p className="text-slate-300 mt-2">
                Step-by-step setup for local-first HedgeVision with Ollama or CPU-bound models.
              </p>
            </div>
            <StepBadge current={wizard.step} />
          </div>
        </div>

        <div className="rounded-2xl border border-white/10 bg-slate-900/60 p-6">
          {wizard.step === 1 && (
            <div className="space-y-4">
              <h2 className="text-xl font-semibold">Step 1: Data Backend</h2>
              <p className="text-slate-300">Choose where to store runtime data.</p>
              <div className="grid md:grid-cols-2 gap-3">
                <button
                  onClick={() => wizard.setDataBackend("sqlite")}
                  className={`p-4 rounded-xl border text-left ${
                    wizard.dataBackend === "sqlite"
                      ? "border-cyan-400 bg-cyan-500/10"
                      : "border-slate-700 bg-slate-800/40"
                  }`}
                >
                  <p className="font-semibold">SQLite (Recommended)</p>
                  <p className="text-sm text-slate-400">Fully local, zero external DB dependency.</p>
                </button>
                <button
                  onClick={() => wizard.setDataBackend("supabase")}
                  className={`p-4 rounded-xl border text-left ${
                    wizard.dataBackend === "supabase"
                      ? "border-cyan-400 bg-cyan-500/10"
                      : "border-slate-700 bg-slate-800/40"
                  }`}
                >
                  <p className="font-semibold">Supabase</p>
                  <p className="text-sm text-slate-400">Optional hosted Postgres mode.</p>
                </button>
              </div>
            </div>
          )}

          {wizard.step === 2 && (
            <div className="space-y-4">
              <h2 className="text-xl font-semibold">Step 2: Model Runtime</h2>
              <p className="text-slate-300">Pick local inference mode for market intelligence.</p>
              <div className="grid md:grid-cols-3 gap-3">
                {[
                  { key: "rules", title: "Rules", body: "Fast deterministic baseline." },
                  { key: "ollama", title: "Ollama", body: "Local LLM server (offline-capable)." },
                  { key: "cpu", title: "CPU Local", body: "CPU-bound local model path." },
                ].map((item) => (
                  <button
                    key={item.key}
                    onClick={() => wizard.setModelRuntime(item.key as "rules" | "ollama" | "cpu")}
                    className={`p-4 rounded-xl border text-left ${
                      wizard.modelRuntime === item.key
                        ? "border-cyan-400 bg-cyan-500/10"
                        : "border-slate-700 bg-slate-800/40"
                    }`}
                  >
                    <p className="font-semibold">{item.title}</p>
                    <p className="text-sm text-slate-400">{item.body}</p>
                  </button>
                ))}
              </div>
              {wizard.modelRuntime === "ollama" && (
                <div className="grid md:grid-cols-2 gap-3">
                  <input
                    value={wizard.modelName}
                    onChange={(e) => wizard.setModelName(e.target.value)}
                    placeholder="Model (e.g. llama3.2)"
                    className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg"
                  />
                  <input
                    value={wizard.ollamaBaseUrl}
                    onChange={(e) => wizard.setOllamaBaseUrl(e.target.value)}
                    placeholder="Ollama URL"
                    className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg"
                  />
                </div>
              )}
              {wizard.modelRuntime === "cpu" && (
                <div className="grid md:grid-cols-3 gap-3">
                  <select
                    value={wizard.cpuBackend}
                    onChange={(e) => wizard.setCpuBackend(e.target.value as "numpy" | "sklearn" | "onnx")}
                    className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg"
                    title="CPU backend"
                  >
                    <option value="numpy">numpy (built-in)</option>
                    <option value="sklearn">sklearn</option>
                    <option value="onnx">onnx</option>
                  </select>
                  <input
                    value={wizard.modelName}
                    onChange={(e) => wizard.setModelName(e.target.value)}
                    placeholder="CPU model name"
                    className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg"
                  />
                  <input
                    value={wizard.cpuModelPath}
                    onChange={(e) => wizard.setCpuModelPath(e.target.value)}
                    placeholder="Local model path (optional)"
                    className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg"
                  />
                </div>
              )}
            </div>
          )}

          {wizard.step === 3 && (
            <div className="space-y-4">
              <h2 className="text-xl font-semibold">Step 3: Broker Mode</h2>
              <p className="text-slate-300">Choose execution backend.</p>
              <div className="grid md:grid-cols-2 gap-3">
                <button
                  onClick={() => wizard.setBrokerBackend("paper")}
                  className={`p-4 rounded-xl border text-left ${
                    wizard.brokerBackend === "paper"
                      ? "border-cyan-400 bg-cyan-500/10"
                      : "border-slate-700 bg-slate-800/40"
                  }`}
                >
                  <p className="font-semibold">Paper (Recommended)</p>
                  <p className="text-sm text-slate-400">Safe local simulation.</p>
                </button>
                <button
                  onClick={() => wizard.setBrokerBackend("ccxt")}
                  className={`p-4 rounded-xl border text-left ${
                    wizard.brokerBackend === "ccxt"
                      ? "border-cyan-400 bg-cyan-500/10"
                      : "border-slate-700 bg-slate-800/40"
                  }`}
                >
                  <p className="font-semibold">CCXT</p>
                  <p className="text-sm text-slate-400">Optional exchange integration.</p>
                </button>
              </div>
              {wizard.brokerBackend === "ccxt" && (
                <input
                  value={wizard.ccxtExchange}
                  onChange={(e) => wizard.setCcxtExchange(e.target.value)}
                  placeholder="Exchange (binance, kraken...)"
                  className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg"
                />
              )}
            </div>
          )}

          {wizard.step === 4 && (
            <div className="space-y-4">
              <h2 className="text-xl font-semibold">Step 4: Generated Env Snippet</h2>
              <p className="text-slate-300">
                Copy this into `backend/api/.env` or run `hedgevision-cli onboard` in terminal.
              </p>
              <pre className="bg-slate-950 border border-slate-800 rounded-xl p-4 overflow-x-auto text-sm text-cyan-200">
                {envSnippet}
              </pre>
              <button
                onClick={copySnippet}
                className="px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white inline-flex items-center gap-2"
              >
                <Copy size={16} /> {copied ? "Copied" : "Copy Env Snippet"}
              </button>
            </div>
          )}

          {wizard.step === 5 && (
            <div className="space-y-4">
              <h2 className="text-xl font-semibold">Step 5: Apply & Start</h2>
              <p className="text-slate-300">
                Apply runtime settings to UI and jump to Signals page.
              </p>
              <div className="rounded-xl border border-slate-700 p-4 bg-slate-800/40 text-sm space-y-1">
                <p>Data backend: {wizard.dataBackend}</p>
                <p>Model runtime: {wizard.modelRuntime}</p>
                <p>Broker backend: {wizard.brokerBackend}</p>
              </div>
              <button
                onClick={finish}
                className="px-5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-medium"
              >
                Finish Onboarding
              </button>
            </div>
          )}

          <div className="mt-8 flex items-center justify-between">
            <button
              onClick={goPrev}
              disabled={wizard.step === 1}
              className="px-4 py-2 rounded-lg border border-slate-700 text-slate-200 disabled:opacity-40 inline-flex items-center gap-2"
            >
              <ChevronLeft size={16} /> Back
            </button>
            <button
              onClick={goNext}
              disabled={wizard.step === TOTAL_STEPS}
              className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-40 inline-flex items-center gap-2"
            >
              Next <ChevronRight size={16} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

