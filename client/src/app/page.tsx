"use client";

import { useRouter } from "next/navigation";
import {
  GitBranch,
  ArrowRight,
  Signal,
  Brain,
  BarChart3,
  Play,
  Cpu,
  Zap,
  GitCompare,
  Database,
  Settings2,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";

export default function LandingPage() {
  const router = useRouter();

  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground font-sans selection:bg-primary selection:text-primary-foreground">
      {/* HEADER */}
      <header className="fixed top-0 z-50 w-full border-b border-border bg-background/80 backdrop-blur-sm">
        <div className="flex h-16 items-center justify-between px-6 lg:px-8">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded bg-foreground text-background font-bold text-sm">
              FS
            </div>
            <span className="font-semibold tracking-tight">FlowSync</span>
            <span className="hidden text-sm text-muted-foreground sm:inline-block border-l border-border pl-3">
              Smart Traffic Control
            </span>
          </div>
          <div className="flex items-center gap-4">
            <Button
              variant="outline"
              size="sm"
              asChild
              className="hidden sm:flex"
            >
              <a
                href="https://github.com/Sri-dinesh/FlowSync"
                target="_blank"
                rel="noopener noreferrer"
              >
                <GitBranch className="mr-2 h-4 w-4" />
                GitHub
              </a>
            </Button>
            <Button size="sm" onClick={() => router.push("/simulation")}>
              Launch App
            </Button>
          </div>
        </div>
      </header>

      <main className="flex-1">
        {/* SECTION 1 — HERO */}
        <section className="relative flex min-h-screen flex-col items-center justify-center px-6 pt-16 text-center lg:px-8">
          {/* Faint dot grid background */}
          <div
            className="pointer-events-none absolute inset-0 opacity-[0.04]"
            style={{
              backgroundImage: `radial-gradient(circle, currentColor 1px, transparent 1px)`,
              backgroundSize: "24px 24px",
            }}
          />

          <div className="relative z-10 max-w-4xl space-y-8">
            <div className="flex justify-center">
              <Badge
                variant="outline"
                className="rounded-full border-border bg-background px-3 py-1 text-xs font-medium text-muted-foreground"
              >
                Reinforcement Learning · Real-time Simulation
              </Badge>
            </div>

            <h1 className="text-5xl font-semibold tracking-tight sm:text-7xl">
              Smart Traffic,
              <br />
              Learned by AI
            </h1>

            <p className="mx-auto max-w-2xl text-lg text-muted-foreground sm:text-xl">
              A Deep Q-Network agent watches your intersection, learns signal
              timing in real time, and consistently outperforms fixed-timer
              systems — live in your browser.
            </p>

            <div className="flex flex-col items-center justify-center gap-4 sm:flex-row">
              <Button
                size="lg"
                className="h-12 px-8 text-base"
                onClick={() => router.push("/simulation")}
              >
                Launch Simulation
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
              <Button
                variant="outline"
                size="lg"
                className="h-12 px-8 text-base"
                asChild
              >
                <a href="#" target="_blank" rel="noopener noreferrer">
                  View on GitHub
                </a>
              </Button>
            </div>

            <div className="flex flex-wrap justify-center gap-3 pt-4">
              {["DQN Agent", "WebSocket Stream", "Live Three.js Viz"].map(
                (pill) => (
                  <Badge
                    key={pill}
                    variant="outline"
                    className="rounded-full border-border bg-background px-3 py-1 text-xs font-normal text-muted-foreground"
                  >
                    {pill}
                  </Badge>
                ),
              )}
            </div>
          </div>
        </section>

        {/* SECTION 2 — HOW IT WORKS */}
        <section className="border-t border-border px-6 py-24 lg:px-8">
          <div className="mx-auto max-w-5xl">
            <div className="space-y-4 text-center">
              <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">
                How it works
              </h2>
              <p className="mx-auto max-w-2xl text-muted-foreground">
                From stochastic vehicle generation to neural network
                optimization.
              </p>
            </div>

            <div className="mt-16 grid grid-cols-1 gap-8 md:grid-cols-3">
              <Card className="border-border bg-card shadow-none">
                <CardContent className="space-y-4 p-8">
                  <div className="flex h-12 w-12 items-center justify-center rounded-lg border border-border bg-muted/50">
                    <Signal className="h-6 w-6" />
                  </div>
                  <h3 className="text-xl font-medium">1. Simulate</h3>
                  <p className="text-sm leading-relaxed text-muted-foreground">
                    Experience a high-fidelity 4-way intersection simulation.
                    Vehicles are dynamically generated using a Poisson
                    distribution to model real-world traffic patterns. A robust
                    fixed-timer controller provides the baseline performance
                    metric.
                  </p>
                </CardContent>
              </Card>

              <Card className="border-border bg-card shadow-none">
                <CardContent className="space-y-4 p-8">
                  <div className="flex h-12 w-12 items-center justify-center rounded-lg border border-border bg-muted/50">
                    <Brain className="h-6 w-6" />
                  </div>
                  <h3 className="text-xl font-medium">2. Train</h3>
                  <p className="text-sm leading-relaxed text-muted-foreground">
                    Deploy a Deep Q-Network (DQN) agent that learns through
                    trial and error. By observing lane queue lengths and vehicle
                    wait times, the AI receives rewards for optimizing flow,
                    eventually discovering complex timing strategies that
                    traditional systems miss.
                  </p>
                </CardContent>
              </Card>

              <Card className="border-border bg-card shadow-none">
                <CardContent className="space-y-4 p-8">
                  <div className="flex h-12 w-12 items-center justify-center rounded-lg border border-border bg-muted/50">
                    <BarChart3 className="h-6 w-6" />
                  </div>
                  <h3 className="text-xl font-medium">3. Compare</h3>
                  <p className="text-sm leading-relaxed text-muted-foreground">
                    Evaluate the AI&apos;s performance against the baseline.
                    Watch as average wait times decrease and throughput
                    increases in real-time. Our dashboard provides granular
                    metrics, showing exactly how much more efficient the AI is
                    compared to fixed intervals.
                  </p>
                </CardContent>
              </Card>
            </div>
          </div>
        </section>

        {/* SECTION 3 — FEATURES */}
        <section className="border-t border-border bg-muted/30 px-6 py-24 lg:px-8">
          <div className="mx-auto max-w-5xl">
            <h2 className="text-center text-2xl font-semibold tracking-tight sm:text-3xl">
              Everything you need
            </h2>

            <div className="mt-16 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {[
                {
                  icon: Play,
                  title: "Live Simulation",
                  body: "Top-down Three.js intersection with real vehicles, lane queues, and switching traffic lights rendered at 10fps via WebSocket.",
                },
                {
                  icon: Cpu,
                  title: "Deep Q-Network",
                  body: "PyTorch DQN with replay buffer, target network, and ε-greedy exploration. State: queue lengths + phase. Action: signal phase selection.",
                },
                {
                  icon: Zap,
                  title: "Real-time Training",
                  body: "Click Train Agent and watch the reward curve climb episode by episode. Training streams live metrics to your browser.",
                },
                {
                  icon: GitCompare,
                  title: "Fixed vs AI Comparison",
                  body: "Run both modes and compare avg wait time, throughput, and max queue length side by side with improvement percentage.",
                },
                {
                  icon: Database,
                  title: "Persistent History",
                  body: "Every simulation, episode, and model checkpoint is saved to Supabase. Load any past model and replay its behavior.",
                },
                {
                  icon: Settings2,
                  title: "Configurable Traffic",
                  body: "Tune vehicle arrival rate (λ) with a slider. Higher λ = more congestion. Test how the AI handles pressure.",
                },
              ].map((feature, i) => (
                <Card
                  key={i}
                  className="border-border bg-card shadow-none transition-colors hover:bg-muted/50"
                >
                  <CardContent className="p-6">
                    <feature.icon className="h-5 w-5" />
                    <h3 className="mt-4 font-medium text-sm">
                      {feature.title}
                    </h3>
                    <p className="mt-2 text-sm text-muted-foreground leading-relaxed">
                      {feature.body}
                    </p>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        </section>

        {/* SECTION 4 — TECH STACK */}
        <section className="border-t border-border px-6 py-24 lg:px-8">
          <div className="mx-auto max-w-4xl text-center">
            <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">
              Built with
            </h2>
            <p className="mt-4 text-muted-foreground">
              Modern stack, clean architecture
            </p>

            <div className="mt-12 space-y-4">
              <div className="flex flex-wrap justify-center gap-3">
                {[
                  "Next.js",
                  "React",
                  "TypeScript",
                  "Three.js",
                  "Tailwind CSS",
                  "Shadcn/ui",
                ].map((tech) => (
                  <div
                    key={tech}
                    className="rounded-full border border-border bg-background px-4 py-1.5 text-sm text-muted-foreground"
                  >
                    {tech}
                  </div>
                ))}
              </div>
              <div className="flex flex-wrap justify-center gap-3">
                {[
                  "FastAPI",
                  "PyTorch",
                  "DQN",
                  "Gymnasium",
                  "WebSockets",
                  "Supabase",
                ].map((tech) => (
                  <div
                    key={tech}
                    className="rounded-full border border-border bg-background px-4 py-1.5 text-sm text-muted-foreground"
                  >
                    {tech}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* SECTION 5 — CTA */}
        <section className="border-t border-border px-6 py-24 lg:px-8">
          <div className="mx-auto max-w-3xl overflow-hidden rounded-2xl bg-foreground text-background">
            <div className="px-8 py-16 text-center sm:px-16">
              <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">
                See the AI learn.
              </h2>
              <p className="mt-6 text-lg text-background/70">
                Open the simulation, hit Train, and watch a neural network
                figure out traffic — in real time.
              </p>
              <div className="mt-10">
                <Button
                  size="lg"
                  className="bg-background text-foreground hover:bg-background/90 h-12 px-8 text-base"
                  onClick={() => router.push("/simulation")}
                >
                  Launch Simulation
                </Button>
              </div>
            </div>
          </div>
        </section>
      </main>

      {/* FOOTER */}
      <footer className="border-t border-border px-6 py-12 lg:px-8">
        <div className="mx-auto flex max-w-5xl flex-col items-center justify-between gap-6 sm:flex-row">
          <div className="space-y-1 text-center sm:text-left">
            <p className="font-semibold tracking-tight">FlowSync</p>
            <p className="text-sm text-muted-foreground">
              Smart Traffic Control · CSE Summer Project 2024-25
            </p>
          </div>
          <p className="text-sm text-muted-foreground">
            Built with Next.js, FastAPI & PyTorch
          </p>
        </div>
      </footer>
    </div>
  );
}
