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
    <div className="relative min-h-screen bg-[#0a0a0a] text-white flex flex-col overflow-hidden">
      <div className="z-50 relative">
        <Header />
      </div>

      <div className="absolute inset-0 z-0">
        <SimulationCanvas />
      </div>

      <main className="flex-1 w-full z-10 pointer-events-none relative mt-[56px]">
        <div className="absolute right-0 top-0 bottom-0 w-full max-w-[420px] pointer-events-auto">
          <aside className="flex flex-col h-[calc(100vh-56px)] overflow-y-auto bg-black/60 backdrop-blur-xl border-l border-white/10 scrollbar-thin scrollbar-thumb-white/20 scrollbar-track-transparent hover:scrollbar-thumb-white/30 shadow-2xl">
            <Card className="rounded-none border-0 border-b border-white/10 bg-transparent flex-none">
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

            <Card className="rounded-none border-0 border-b border-white/10 bg-transparent p-4 flex-none">
              <CardTitle className="mb-3 text-xs uppercase tracking-[0.14em] text-white/35">
                Real-time Metrics
              </CardTitle>
              <MetricsPanel />
            </Card>

            <Card className="rounded-none border-0 bg-transparent flex-none min-h-[300px] overflow-visible pb-10">
              <CardHeader className="pb-3">
                <CardTitle className="text-xs uppercase tracking-[0.14em] text-white/35">
                  Analytics
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-0 pb-6">
                <Tabs defaultValue="training" className="w-full">
                  <TabsList className="h-auto gap-1 bg-transparent p-0">
                    <TabsTrigger
                      value="training"
                      className="text-white/40 hover:text-white/70 data-[state=active]:border-white/20 data-[state=active]:bg-white/10 data-[state=active]:text-white"
                    >
                      Training
                    </TabsTrigger>
                    <TabsTrigger
                      value="comparison"
                      className="text-white/40 hover:text-white/70 data-[state=active]:border-white/20 data-[state=active]:bg-white/10 data-[state=active]:text-white"
                    >
                      Compare
                    </TabsTrigger>
                    <TabsTrigger
                      value="history"
                      className="text-white/40 hover:text-white/70 data-[state=active]:border-white/20 data-[state=active]:bg-white/10 data-[state=active]:text-white"
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
        </div>

        <div className="absolute left-6 bottom-6 w-80 pointer-events-auto hidden lg:block">
          <div className="rounded-xl border border-white/10 bg-black/60 backdrop-blur-xl p-4 shadow-2xl">
            <div className="mb-3 text-[10px] uppercase tracking-[0.14em] text-white/35">
              Live Snapshot
            </div>
            <LiveSnapshot />
          </div>
        </div>
      </main>
    </div>
  );
}
