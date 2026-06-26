"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "@/components/Sidebar";
import { TopBar } from "@/components/TopBar";
import { QueryClient, QueryClientProvider, useQueryClient, useQuery } from "@tanstack/react-query";
import { cn, HW_LABELS } from "@/lib/utils";
import { useDataMode } from "@/hooks/useDataMode";
import { Button } from "@/components/ui/Button";
import { api } from "@/lib/api";

const queryClient = new QueryClient({ 
  defaultOptions: { 
    queries: { refetchInterval: 10000, retry: 1 } 
  } 
});

function DynamicLabelsLoader() {
  const { data: labels } = useQuery({
    queryKey: ["hw-labels"],
    queryFn: async () => {
      try {
        const response = await api.get<Record<string, string>>("/api/devices/labels");
        return response.data;
      } catch {
        return {};
      }
    },
    enabled: useDataMode.getState().mode === "real",
  });

  useEffect(() => {
    if (labels) {
      Object.assign(HW_LABELS, labels);
    }
  }, [labels]);

  return null;
}

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [mounted, setMounted] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [hasToken, setHasToken] = useState<boolean | null>(null);

  useEffect(() => {
    setMounted(true);
    const token = localStorage.getItem("aura_token");
    if (!token) {
      setHasToken(false);
      router.push("/login");
    } else {
      setHasToken(true);
    }
  }, [router]);

  if (!mounted || hasToken === null || hasToken === false) return null;

  return (
    <QueryClientProvider client={queryClient}>
      <DynamicLabelsLoader />
      <div className="flex h-screen overflow-hidden bg-transparent dark:bg-gray-950">
        
        {/* ... Sidebar y Main ... */}
        <Sidebar collapsed={sidebarCollapsed} onToggle={() => setSidebarCollapsed(!sidebarCollapsed)} />
        
        <div className={cn(
          "flex-1 flex flex-col overflow-hidden relative transition-all duration-300",
          sidebarCollapsed ? "ml-0 md:ml-20" : "ml-0 md:ml-56"
        )}>
          {/* ... TopBar y Main ... */}
          <div className="z-10 flex flex-col h-full">
            <TopBar />
            <main className="flex-1 overflow-y-auto p-4 md:p-8 dot-grid scroll-smooth">
              {children}
            </main>
          </div>
        </div>

        <DataModeToggle />
      </div>
    </QueryClientProvider>
  );
}

export function DataModeToggle() {
  const { mode, toggleMode } = useDataMode();
  const queryClient = useQueryClient();

  const handleToggle = () => {
    toggleMode();
    
    // Wipe the cache completely clean instead of just marking it stale.
    // This forces all components to immediately drop the old data and show loading states.
    queryClient.resetQueries(); 
  };

  return (
    <Button 
      variant="outline" 
      onClick={handleToggle}
      className={cn(
        "fixed bottom-4 right-4 z-[999] transition-all duration-300 shadow-lg",
        mode === 'demo' 
          ? "bg-purple-50 border-purple-300 text-purple-700 hover:bg-purple-100 hover:text-purple-800 dark:bg-purple-900/30 dark:border-purple-700 dark:text-purple-400 dark:hover:bg-purple-900/50" 
          : "bg-white dark:bg-gray-950"
      )}
    >
      {mode === 'demo' ? "🧪 Demo Mode (False Data)" : "🌐 Real Mode (API)"}
    </Button>
  );
}