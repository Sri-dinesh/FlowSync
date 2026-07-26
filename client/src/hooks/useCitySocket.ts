"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { getFastApiUrls } from "@/lib/utils";
import type {
  CityFrame,
  ComparisonResult,
  ComparisonResultsFrame,
} from "@/types/city";

const MAX_RETRIES = 5;
const BASE_DELAY_MS = 500;

interface UseCitySocketReturn {
  frame: CityFrame | null;
  connected: boolean;
  comparisonResults: Record<string, ComparisonResult> | null;
  comparisonRunning: boolean;
  sendCommand: (cmd: Record<string, unknown>) => void;
}

import { useSimulationStore } from "@/store/simulationStore";

export function useCitySocket(): UseCitySocketReturn {
  const setCityConnected = useSimulationStore((state) => state.setCityConnected);
  const [frame, setFrame] = useState<CityFrame | null>(null);
  const [connected, setConnected] = useState(false);
  const [comparisonResults, setComparisonResults] = useState<Record<string, ComparisonResult> | null>(null);
  const [comparisonRunning, setComparisonRunning] = useState(false);

  const socketRef = useRef<WebSocket | null>(null);
  const retryRef = useRef(0);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const shouldReconnectRef = useRef(true);
  const connectRef = useRef<(() => void) | null>(null);

  const connect = useCallback(() => {
    const { wsUrl: baseUrl } = getFastApiUrls();
    if (!baseUrl) {
      console.error("[CityWS] Missing NEXT_PUBLIC_FASTAPI_WS_URL");
      setConnected(false);
      return;
    }

    const wsUrl = `${baseUrl}/ws/city`;
    console.log("[CityWS] Connecting to:", wsUrl);
    const socket = new WebSocket(wsUrl);
    socketRef.current = socket;

    socket.onopen = () => {
      retryRef.current = 0;
      setConnected(true);
      setCityConnected(true);
      console.log("%c[CityWS] Connected", "color:#22c55e;font-weight:bold");
    };

    socket.onmessage = (event) => {
      try {
        const raw = JSON.parse(event.data);
        if (!raw || typeof raw !== "object") return;

        if (raw.frame_type === "comparison_results") {
          const rf = raw as ComparisonResultsFrame;
          setComparisonResults(rf.results);
          setComparisonRunning(false);
          return;
        }

        if (raw.frame_type === "comparison_started") {
          setComparisonRunning(true);
          setComparisonResults(null);
          return;
        }

        if (raw.frame_type === "city_simulation") {
          const f = raw as CityFrame;
          setFrame(f);
          if (f.comparison_progress?.running !== undefined) {
            setComparisonRunning(f.comparison_progress.running);
          }
        }
      } catch (err) {
        console.warn("[CityWS] Failed to parse message:", event.data, err);
      }
    };

    socket.onclose = (ev) => {
      setConnected(false);
      setCityConnected(false);
      console.log("%c[CityWS] Disconnected", "color:#f97316;font-weight:bold", {
        code: ev.code,
        reason: ev.reason || "(none)",
      });

      if (!shouldReconnectRef.current || retryRef.current >= MAX_RETRIES) return;

      const delay = BASE_DELAY_MS * Math.pow(2, retryRef.current);
      retryRef.current += 1;
      reconnectTimeoutRef.current = setTimeout(() => {
        connectRef.current?.();
      }, delay);
    };

    socket.onerror = () => {
      console.error("[CityWS] Connection error.");
      socket.close();
    };
  }, []);

  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

  useEffect(() => {
    shouldReconnectRef.current = true;
    const t = setTimeout(connect, 0);
    return () => {
      shouldReconnectRef.current = false;
      clearTimeout(t);
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      socketRef.current?.close();
    };
  }, [connect]);

  const sendCommand = useCallback((cmd: Record<string, unknown>) => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      console.log("[CityWS] → COMMAND:", cmd);
      socketRef.current.send(JSON.stringify(cmd));
    } else {
      console.warn("[CityWS] Socket not open. State:", socketRef.current?.readyState);
    }
  }, []);

  return { frame, connected, comparisonResults, comparisonRunning, sendCommand };
}
