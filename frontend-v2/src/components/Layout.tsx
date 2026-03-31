import React from "react";
import { DashboardHeader } from "./DashboardHeader";

export function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen">
      <DashboardHeader />
      <main className="pt-16 px-3 sm:px-5 md:px-8 pb-10 max-w-[1800px] mx-auto">
        {children}
      </main>
    </div>
  );
}
