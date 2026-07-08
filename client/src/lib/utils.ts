import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function getFastApiUrls() {
  let httpUrl = process.env.NEXT_PUBLIC_FASTAPI_HTTP_URL || "";
  let wsUrl = process.env.NEXT_PUBLIC_FASTAPI_WS_URL || "";

  // Ensure fallback defaults if still empty
  if (!httpUrl) httpUrl = "http://127.0.0.1:8000";
  if (!wsUrl) wsUrl = "ws://127.0.0.1:8000";

  return { httpUrl, wsUrl };
}
