"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { login } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

export default function LoginPage() {
  const router = useRouter();
  const [form, setForm] = useState({ username: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // --- ADD THIS BLOCK TO SKIP LOGIN ---
  useEffect(() => {
    // Set a dummy token (or a real one if you generated one via Postman)
    localStorage.setItem("aura_token", "dev_bypass_token");
    router.push("/dashboard");
  }, [router]);
  // ------------------------------------

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true); setError("");
    try {
      const token = await login(form.username, form.password);
      localStorage.setItem("aura_token", token);
      router.push("/dashboard");
    } catch {
      setError("Invalid credentials");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="w-full max-w-sm animate-fade-in">
      <div className="flex flex-col items-center gap-3 mb-8">
        <div className="w-12 h-12 rounded-2xl bg-aura-accent flex items-center justify-center glow-accent">
          <span className="text-white text-xl font-bold font-mono">A</span>
        </div>
        <div className="text-center">
          <h1 className="text-xl font-semibold text-aura-text">AURA Platform</h1>
          <p className="text-xs text-aura-dim mt-1 font-mono">Edge AI Deployment</p>
        </div>
      </div>
      <div className="bg-aura-surface border border-aura-border rounded-2xl p-6 shadow-xl">
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <Input label="Username" value={form.username}
            onChange={e => setForm(f => ({ ...f, username: e.target.value }))}
            placeholder="admin" autoComplete="username" required />
          <Input label="Password" type="password" value={form.password}
            onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
            placeholder="••••••••" autoComplete="current-password" required />
          {error && <p className="text-xs text-aura-danger text-center">{error}</p>}
          <Button type="submit" loading={loading} className="w-full justify-center mt-1">
            Sign in
          </Button>
        </form>
      </div>
    </div>
  );
}
