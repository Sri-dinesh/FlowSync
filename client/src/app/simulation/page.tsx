"use client";

import Header from "@/components/layout/Header";
import SimulationControls from "@/components/controls/SimulationControls";
import TrainingControls from "@/components/controls/TrainingControls";
import ComparisonChart from "@/components/dashboard/ComparisonChart";
import EpisodeHistory from "@/components/dashboard/EpisodeHistory";
import LiveSnapshot from "@/components/dashboard/LiveSnapshot";
import MetricsPanel from "@/components/dashboard/MetricsPanel";
import TrainingChart from "@/components/dashboard/TrainingChart";
import SimulationCanvas from "@/components/simulation/SimulationCanvas";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useSimulationSocket } from "@/hooks/useSimulationSocket";
import { useTrainingSocket } from "@/hooks/useTrainingSocket";
import { useSimulations } from "@/hooks/useSimulations";

export default function SimulationPage() {
  const { sendCommand: sendSimulationCommand } = useSimulationSocket();
  const { sendCommand: sendTrainingCommand } = useTrainingSocket();
  const { data: simulations = [] } = useSimulations();
  const simulationId = simulations[0]?.id ?? null;

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-white">
      <Header />

      <main className="mx-auto grid h-[calc(100vh-56px)] w-full max-w-[1200px] gap-0 lg:grid-cols-[1fr_320px]">
        <section className="flex flex-col gap-6">
          <Card className="h-full rounded-none border-0 border-r border-white/10 bg-[#0f0f0f]">
            <CardHeader className="pb-2">
              <CardTitle className="text-xs uppercase tracking-[0.14em] text-white/35">
                Simulation Canvas
              </CardTitle>
            </CardHeader>
            <CardContent className="h-[calc(100%-52px)] border-y border-white/10 bg-black/40 p-0">
              <SimulationCanvas />
            </CardContent>
            <CardContent className="border-b border-white/10 bg-[#111111] p-4">
              <CardTitle className="mb-3 text-xs uppercase tracking-[0.14em] text-white/35">
                Live Snapshot
              </CardTitle>
              <LiveSnapshot />
            </CardContent>
          </Card>
        </section>

        <aside className="flex h-full flex-col overflow-hidden border-l border-white/10 bg-[#111111]">
          <Card className="rounded-none border-0 border-b border-white/10 bg-transparent">
            <CardHeader className="pb-3">
              <CardTitle className="text-xs uppercase tracking-[0.14em] text-white/35">
                Controls
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-5 pb-4">
              <SimulationControls sendCommand={sendSimulationCommand} />
              <TrainingControls
                sendCommand={sendTrainingCommand}
                simulationId={simulationId}
              />
            </CardContent>
          </Card>

          <div className="border-b border-white/10 p-4">
            <MetricsPanel />
          </div>

          <Card className="flex-1 rounded-none border-0 bg-transparent">
            <CardHeader className="pb-3">
              <CardTitle className="text-xs uppercase tracking-[0.14em] text-white/35">
                Analytics
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-0">
              <Tabs defaultValue="training" className="w-full">
                <TabsList className="h-auto gap-1 bg-transparent p-0">
                  <TabsTrigger
                    value="training"
                    className="data-[state=active]:border-white/20 data-[state=active]:bg-[#1a1a1a] data-[state=active]:text-white"
                  >
                    Training
                  </TabsTrigger>
                  <TabsTrigger
                    value="comparison"
                    className="data-[state=active]:border-white/20 data-[state=active]:bg-[#1a1a1a] data-[state=active]:text-white"
                  >
                    Compare
                  </TabsTrigger>
                  <TabsTrigger
                    value="history"
                    className="data-[state=active]:border-white/20 data-[state=active]:bg-[#1a1a1a] data-[state=active]:text-white"
                  >
                    History
                  </TabsTrigger>
                </TabsList>
                <TabsContent
                  value="training"
                  className="mt-4 text-sm text-white/70"
                >
                  <TrainingChart />
                </TabsContent>
                <TabsContent
                  value="comparison"
                  className="mt-4 text-sm text-white/70"
                >
                  <ComparisonChart simulationId={simulationId} />
                </TabsContent>
                <TabsContent
                  value="history"
                  className="mt-4 text-sm text-white/70"
                >
                  <EpisodeHistory simulationId={simulationId} />
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>
        </aside>
      </main>
    </div>
  );
}
