import { create } from "zustand";
import { persist } from "zustand/middleware";

export type WizardDataBackend = "sqlite" | "supabase";
export type WizardModelRuntime = "rules" | "ollama" | "cpu";
export type WizardCpuBackend = "numpy" | "sklearn" | "onnx";
export type WizardBrokerBackend = "paper" | "ccxt";

interface OnboardingState {
  completed: boolean;
  step: number;
  dataBackend: WizardDataBackend;
  modelRuntime: WizardModelRuntime;
  modelName: string;
  ollamaBaseUrl: string;
  cpuBackend: WizardCpuBackend;
  cpuModelPath: string;
  brokerBackend: WizardBrokerBackend;
  ccxtExchange: string;
  markCompleted: (done: boolean) => void;
  setStep: (step: number) => void;
  setDataBackend: (dataBackend: WizardDataBackend) => void;
  setModelRuntime: (modelRuntime: WizardModelRuntime) => void;
  setModelName: (modelName: string) => void;
  setOllamaBaseUrl: (ollamaBaseUrl: string) => void;
  setCpuBackend: (cpuBackend: WizardCpuBackend) => void;
  setCpuModelPath: (cpuModelPath: string) => void;
  setBrokerBackend: (brokerBackend: WizardBrokerBackend) => void;
  setCcxtExchange: (ccxtExchange: string) => void;
}

export const useOnboardingStore = create<OnboardingState>()(
  persist(
    (set) => ({
      completed: false,
      step: 1,
      dataBackend: "sqlite",
      modelRuntime: "rules",
      modelName: "llama3.2",
      ollamaBaseUrl: "http://localhost:11434",
      cpuBackend: "numpy",
      cpuModelPath: "",
      brokerBackend: "paper",
      ccxtExchange: "binance",
      markCompleted: (completed) => set({ completed }),
      setStep: (step) => set({ step }),
      setDataBackend: (dataBackend) => set({ dataBackend }),
      setModelRuntime: (modelRuntime) => set({ modelRuntime }),
      setModelName: (modelName) => set({ modelName }),
      setOllamaBaseUrl: (ollamaBaseUrl) => set({ ollamaBaseUrl }),
      setCpuBackend: (cpuBackend) => set({ cpuBackend }),
      setCpuModelPath: (cpuModelPath) => set({ cpuModelPath }),
      setBrokerBackend: (brokerBackend) => set({ brokerBackend }),
      setCcxtExchange: (ccxtExchange) => set({ ccxtExchange }),
    }),
    { name: "hedgevision-onboarding" },
  ),
);

