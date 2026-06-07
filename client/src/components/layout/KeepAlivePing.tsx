"use client";

import { useEffect } from "react";

export function KeepAlivePing() {
  useEffect(() => {
    fetch("/api/keep-alive")
      .then((res) => {
        if (res.ok) {
          console.log("[KeepAlive] Backend wake-up ping sent.");
        }
      })
      .catch((err) => {
        console.warn("[KeepAlive] Wake-up ping failed:", err);
      });
  }, []);

  return null;
}
