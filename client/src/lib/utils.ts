import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function getFastApiUrls() {
  let httpUrl = process.env.NEXT_PUBLIC_FASTAPI_HTTP_URL || "";
  let wsUrl = process.env.NEXT_PUBLIC_FASTAPI_WS_URL || "";

  let isLocalhost = true;
  if (typeof window !== "undefined") {
    const hostname = window.location.hostname;
    isLocalhost =
      hostname === "localhost" ||
      hostname === "127.0.0.1" ||
      hostname === "[::1]" ||
      hostname.startsWith("192.168.") ||
      hostname.startsWith("10.") ||
      hostname.endsWith(".local");
  } else {
    isLocalhost = process.env.NODE_ENV !== "production";
  }

  if (!isLocalhost) {
    if (!httpUrl || httpUrl.includes("localhost") || httpUrl.includes("127.0.0.1")) {
      httpUrl = "https://flowsync-gelt.onrender.com";
    }
    if (!wsUrl || wsUrl.includes("localhost") || wsUrl.includes("127.0.0.1")) {
      wsUrl = "wss://flowsync-gelt.onrender.com";
    }
  }

  // Ensure fallback defaults if still empty
  if (!httpUrl) httpUrl = "http://127.0.0.1:8000";
  if (!wsUrl) wsUrl = "ws://127.0.0.1:8000";

  return { httpUrl, wsUrl };
}
