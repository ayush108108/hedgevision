import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getWatchlist, addToWatchlist, removeFromWatchlist, WatchItem } from "../services/watchlist";
import { Plus, Trash2, Star } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { WaitlistCTA } from "../components/common/WaitlistCTA";

export function WatchlistPage() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [asset1, setAsset1] = useState("");
  const [asset2, setAsset2] = useState("");
  const [granularity, setGranularity] = useState("daily");

  const { data: items = [] } = useQuery<WatchItem[]>({
    queryKey: ["watchlist"],
    queryFn: async () => getWatchlist(),
    staleTime: 0, // Always refetch to reflect new additions
    refetchOnMount: true, // Refetch when component mounts
  });

  const addMutation = useMutation({
    mutationFn: async () => addToWatchlist(asset1.trim().toUpperCase(), asset2.trim().toUpperCase(), granularity),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["watchlist"] });
      setAsset1("");
      setAsset2("");
      // Navigate to cointegration screener with the added pair
      navigate(`/cointegration?asset1=${asset1.toUpperCase()}&asset2=${asset2.toUpperCase()}&view=test`);
    },
  });

  const removeMutation = useMutation({
    mutationFn: async (id: string) => removeFromWatchlist(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["watchlist"] }),
  });

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div className="premium-card p-4 sm:p-8">
        <div className="flex items-center gap-3 mb-3">
          <Star className="h-6 w-6 text-yellow-400" />
          <h1 className="text-xl sm:text-2xl font-bold text-white">Watchlist</h1>
        </div>
        <p className="text-sm sm:text-base text-gray-400">Track pairs you're interested in and jump straight to analysis.</p>
      </div>

      <div className="premium-card p-4 sm:p-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          <input
            value={asset1}
            onChange={(e) => setAsset1(e.target.value)}
            placeholder="Asset 1 (e.g., AAPL)"
            className="px-4 py-2.5 bg-white/5 border border-gray-700 rounded-lg text-white"
          />
          <input
            value={asset2}
            onChange={(e) => setAsset2(e.target.value)}
            placeholder="Asset 2 (e.g., MSFT)"
            className="px-4 py-2.5 bg-white/5 border border-gray-700 rounded-lg text-white"
          />
          <select
            aria-label="Granularity"
            value={granularity}
            onChange={(e) => setGranularity(e.target.value)}
            className="px-4 py-2.5 bg-white/5 border border-gray-700 rounded-lg text-white appearance-none cursor-pointer"
          >
            <option value="daily" className="bg-gray-800 text-white">Daily</option>
            <option value="4h" className="bg-gray-800 text-white">4 Hour</option>
          </select>
          <button
            onClick={() => addMutation.mutate()}
            disabled={!asset1 || !asset2 || addMutation.isPending}
            className="px-4 py-2.5 rounded-lg bg-blue-500/20 hover:bg-blue-500/30 text-blue-300 border border-blue-500/30 flex items-center gap-2"
          >
            <Plus className="w-4 h-4" /> Add
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {items.map((i) => (
          <div key={i.id} className="p-4 sm:p-5 rounded-xl sm:rounded-2xl bg-white/5 border border-white/10 flex items-center justify-between gap-3">
            <div>
              <div className="text-white font-semibold">
                {i.asset1} / {i.asset2}
              </div>
              <div className="text-xs text-gray-400">{i.granularity || "daily"} • Added {new Date(i.addedAt).toLocaleDateString()}</div>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => navigate(`/cointegration?asset1=${i.asset1}&asset2=${i.asset2}`)}
                className="px-3 py-1.5 rounded-lg bg-white/10 text-white text-sm"
              >
                Analyze
              </button>
              <button
                onClick={() => removeMutation.mutate(i.id)}
                className="p-2 rounded-lg bg-red-500/10 text-red-400 border border-red-500/30"
                title="Remove"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          </div>
        ))}
        {items.length === 0 && (
          <div className="p-6 sm:p-12 text-center rounded-xl sm:rounded-2xl border-2 border-dashed border-white/10 bg-white/5 text-gray-400">
            No items yet. Add a pair above to get started.
          </div>
        )}
      </div>

      <WaitlistCTA
        title="Want Early Access to Advanced Features?"
        description="Join our waitlist to get notified when new watchlist features and AI-powered recommendations go live."
        sourcePage="watchlist"
        sourceLabel="watchlist-page-cta"
      />
    </div>
  );
}
