"use client";

import Header from "@/components/layout/Header";
import SimulationCanvas from "@/components/simulation/SimulationCanvas";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useSimulationSocket } from "@/hooks/useSimulationSocket";
import { useTrainingSocket } from "@/hooks/useTrainingSocket";

export default function SimulationPage() {
  useSimulationSocket();
  useTrainingSocket();

  return (
    <div className="min-h-screen bg-[#0b0f14] text-white">
      <div className="absolute inset-0 -z-10 bg-[radial-gradient(circle_at_top,rgba(56,189,248,0.12),transparent_55%)]" />
      <Header />

      <main className="mx-auto grid w-full max-w-6xl gap-6 px-6 py-8 lg:grid-cols-[3fr_2fr]">
        <section className="flex flex-col gap-6">
          <Card className="min-h-[420px] border-white/10 bg-white/5 shadow-[0_0_30px_rgba(56,189,248,0.12)]">
            <CardHeader>
              <CardTitle>Simulation Canvas</CardTitle>
            </CardHeader>
            <CardContent className="rounded-xl border border-white/10 bg-black/40 p-3">
              <SimulationCanvas />
            </CardContent>
          </Card>

          <Card className="border-white/10 bg-white/5">
            <CardHeader>
              <CardTitle>Live Snapshot</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-white/70">
              Metrics, queue lengths, and status tiles land here in Phase 7.
            </CardContent>
          </Card>
        </section>

        <aside className="flex flex-col gap-6">
          <Card className="border-white/10 bg-white/5">
            <CardHeader>
              <CardTitle>Controls</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-white/70">
              Simulation and training controls will be assembled in Phase 7.
            </CardContent>
          </Card>

          <Card className="border-white/10 bg-white/5">
            <CardHeader>
              <CardTitle>Analytics</CardTitle>
            </CardHeader>
            <CardContent>
              <Tabs defaultValue="training" className="w-full">
                <TabsList className="bg-white/5">
                  <TabsTrigger value="training">Training</TabsTrigger>
                  <TabsTrigger value="comparison">Compare</TabsTrigger>
                </TabsList>
                <TabsContent
                  value="training"
                  className="mt-4 text-sm text-white/70"
                >
                  Reward and loss charts appear here in Phase 7.
                </TabsContent>
                <TabsContent
                  value="comparison"
                  className="mt-4 text-sm text-white/70"
                >
                  Fixed vs AI comparison charts appear here in Phase 7.
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>
        </aside>
      </main>
    </div>
  );
}
