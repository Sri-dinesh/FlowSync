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
    <div className="relative h-screen bg-[#0a0a0a] text-white flex flex-col overflow-hidden">
      <div className="z-50 relative flex-none">
        <Header />
      </div>

      <div className="flex-1 flex w-full overflow-hidden">
        {/* Left Side: 3D Canvas */}
        <div className="flex-1 relative">
          <SimulationCanvas />
        </div>

        {/* Right Side: Controls Sidebar */}
        <aside className="w-[420px] flex-shrink-0 flex flex-col h-full overflow-y-auto bg-black/60 backdrop-blur-xl border-l border-white/10 scrollbar-thin scrollbar-thumb-white/20 scrollbar-track-transparent hover:scrollbar-thumb-white/30 shadow-2xl z-10 pointer-events-auto">
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

          <Card className="rounded-none border-0 border-b border-white/10 bg-transparent p-4 flex-none">
            <CardTitle className="mb-3 text-xs uppercase tracking-[0.14em] text-white/35">
              Live Snapshot
            </CardTitle>
            <LiveSnapshot />
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
    </div>
  );
}
