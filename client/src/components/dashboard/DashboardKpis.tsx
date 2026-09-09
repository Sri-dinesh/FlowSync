"use client";

import { useEffect, useRef } from "react";
import { motion } from "framer-motion";
import gsap from "gsap";
import { Car, Clock, Leaf, Zap, ShieldCheck, TrendingDown } from "lucide-react";

export interface DashboardOverviewData {
  total_sessions: number;
  total_vehicles_processed: number;
  total_frames_processed: number;
  total_footage_duration_s: number;
  total_footage_hours: number;
  avg_intersection_wait_s: number;
  total_movement_occurrences: number;
  peak_queue_observed: number;
  avg_detection_fps: number;
  avg_wait_reduction_pct: number;
  inference_latency_ms: number;
  ai_reliability_score: number;
}

interface Props {
  data: DashboardOverviewData;
}

export default function DashboardKpis({ data }: Props) {
  const vehRef = useRef<HTMLSpanElement>(null);
  const waitRef = useRef<HTMLSpanElement>(null);
  const delayRef = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    // GSAP animated count-ups for numerical values
    const ctx = gsap.context(() => {
      if (vehRef.current) {
        const obj = { val: 0 };
        gsap.to(obj, {
          val: data.total_vehicles_processed,
          duration: 1.8,
          ease: "power2.out",
          onUpdate: () => {
            if (vehRef.current) {
              vehRef.current.innerText = Math.round(obj.val).toLocaleString();
            }
          },
        });
      }

      if (waitRef.current) {
        const obj = { val: 0 };
        gsap.to(obj, {
          val: data.avg_wait_reduction_pct,
          duration: 1.6,
          ease: "power2.out",
          onUpdate: () => {
            if (waitRef.current) {
              waitRef.current.innerText = `-${obj.val.toFixed(1)}%`;
            }
          },
        });
      }

      if (delayRef.current) {
        const obj = { val: 0 };
        gsap.to(obj, {
          val: data.avg_intersection_wait_s,
          duration: 1.8,
          ease: "power2.out",
          onUpdate: () => {
            if (delayRef.current) {
              delayRef.current.innerText = `${obj.val.toFixed(1)} s`;
            }
          },
        });
      }
    });

    return () => ctx.revert();
  }, [data]);

  const cards = [
    {
      title: "Total Vehicles Analyzed",
      ref: vehRef,
      fallback: data.total_vehicles_processed.toLocaleString(),
      subtitle: `${data.total_sessions} simulation runs (${data.total_movement_occurrences.toLocaleString()} passages)`,
      badge: "+100% Real Tracking",
      badgeColor: "bg-blue-500/10 text-blue-400 border-blue-500/20",
      icon: Car,
      gradient: "from-blue-500/20 via-indigo-500/10 to-transparent",
      borderColor: "border-blue-500/30",
    },
    {
      title: "Avg Wait-Time Reduction",
      ref: waitRef,
      fallback: `-${data.avg_wait_reduction_pct.toFixed(1)}%`,
      subtitle: "DQN AI Policy vs Standard Fixed Baseline",
      badge: "Peak Efficiency",
      badgeColor: "bg-amber-500/10 text-amber-300 border-amber-500/20",
      icon: TrendingDown,
      gradient: "from-amber-500/20 via-orange-500/10 to-transparent",
      borderColor: "border-amber-500/30",
    },
    {
      title: "Average Vehicle Delay",
      ref: delayRef,
      fallback: `${data.avg_intersection_wait_s.toFixed(1)} s`,
      subtitle: `Mean queue delay across ${data.total_frames_processed.toLocaleString()} frames (Peak: ${data.peak_queue_observed} veh)`,
      badge: "Telemetry Mean",
      badgeColor: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
      icon: Clock,
      gradient: "from-emerald-500/20 via-teal-500/10 to-transparent",
      borderColor: "border-emerald-500/30",
    },
    {
      title: "AI Policy Decision Speed",
      ref: null,
      customValue: `${data.inference_latency_ms}ms`,
      subtitle: `${data.total_footage_hours}h footage evaluated at ${data.avg_detection_fps} FPS`,
      badge: "Real-time Edge",
      badgeColor: "bg-purple-500/10 text-purple-400 border-purple-500/20",
      icon: Zap,
      gradient: "from-purple-500/20 via-pink-500/10 to-transparent",
      borderColor: "border-purple-500/30",
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map((card, i) => {
        const Icon = card.icon;
        return (
          <motion.div
            key={card.title}
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: i * 0.1 }}
            whileHover={{ y: -3, transition: { duration: 0.2 } }}
            className={`relative overflow-hidden rounded-2xl border ${card.borderColor} bg-white/[0.02] p-5 shadow-xl backdrop-blur-md transition-all`}
          >
            {/* Ambient Background Gradient */}
            <div
              className={`pointer-events-none absolute -right-6 -top-6 h-28 w-28 rounded-full bg-gradient-to-br ${card.gradient} blur-2xl`}
            />

            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-white/50">
                {card.title}
              </span>
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-white/5 border border-white/10 text-white/80">
                <Icon className="h-4 w-4" />
              </div>
            </div>

            <div className="mt-3 flex items-baseline gap-2">
              <span
                ref={card.ref}
                className="text-2xl font-bold font-mono text-white tracking-tight"
              >
                {card.customValue || card.fallback}
              </span>
              <span
                className={`text-[9px] font-semibold px-2 py-0.5 rounded-full border ${card.badgeColor}`}
              >
                {card.badge}
              </span>
            </div>

            <p className="mt-2 text-[11px] text-white/40 leading-relaxed">
              {card.subtitle}
            </p>
          </motion.div>
        );
      })}
    </div>
  );
}
