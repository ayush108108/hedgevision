import { create } from "zustand";
import { persist } from "zustand/middleware";

export type BYOKProvider = "rules" | "openai" | "anthropic" | "ollama" | "cpu";

interface BYOKState {
  provider: BYOKProvider;
  model: string;
  useLlm: boolean;
  setProvider: (provider: BYOKProvider) => void;
  setModel: (model: string) => void;
  setUseLlm: (useLlm: boolean) => void;
}

export const useBYOKStore = create<BYOKState>()(
  persist(
    (set) => ({
      provider: "rules",
      model: "llama3.2",
      useLlm: false,
      setProvider: (provider) => set({ provider }),
      setModel: (model) => set({ model }),
      setUseLlm: (useLlm) => set({ useLlm }),
    }),
    {
      name: "hedgevision-byok-config",
    },
  ),
);
