"use client";

import { useRouter } from "next/navigation";
import { Space_Grotesk } from "next/font/google";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

const display = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-display",
});

export default function Home() {
  const router = useRouter();

  return (
    <div
      className={`relative flex min-h-screen items-center justify-center overflow-hidden bg-[#0b0f14] text-white ${display.variable}`}
    >
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(56,189,248,0.18),transparent_55%)]" />
      <div className="pointer-events-none absolute inset-0 opacity-40 [background-size:56px_56px] [background-image:linear-gradient(to_right,rgba(148,163,184,0.12)_1px,transparent_1px),linear-gradient(to_bottom,rgba(148,163,184,0.12)_1px,transparent_1px)]" />
      <div className="pointer-events-none absolute -bottom-32 left-1/2 h-64 w-[80vw] -translate-x-1/2 rounded-full bg-gradient-to-r from-amber-400/20 via-transparent to-cyan-400/20 blur-3xl" />

      <main className="relative z-10 mx-auto flex w-full max-w-5xl flex-col items-center gap-8 px-6 text-center">
        <Badge
          className="border-white/20 bg-white/10 text-white/80"
          variant="outline"
        >
          AI Traffic Control Lab
        </Badge>
        <h1 className="max-w-3xl text-4xl font-semibold leading-tight tracking-tight md:text-6xl md:leading-tight font-[var(--font-display)]">
          Orchestrate smarter intersections with live reinforcement learning.
        </h1>
        <p className="max-w-2xl text-base text-white/70 md:text-lg">
          Train a DQN agent, stream live simulation frames, and compare fixed
          timers against adaptive signals in real time.
        </p>
        <div className="flex flex-col items-center gap-3 sm:flex-row">
          <Button
            size="lg"
            className="bg-white text-black hover:bg-white/90"
            onClick={() => router.push("/simulation")}
          >
            Launch Simulation
          </Button>
          <Button
            size="lg"
            variant="outline"
            className="border-white/30 text-white hover:bg-white/10"
            onClick={() => router.push("/simulation")}
          >
            View Dashboard
          </Button>
        </div>
      </main>
    </div>
  );
}
