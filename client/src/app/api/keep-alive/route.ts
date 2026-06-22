import { NextResponse } from "next/server";
import { getFastApiUrls } from "@/lib/utils";

/**
 * API route to keep the backend server awake.
 * It pings the FastAPI backend's health endpoint.
 * This can be triggered by a Cron job or GitHub Action.
 */
export async function GET() {
  const { httpUrl, wsUrl } = getFastApiUrls();

  const backendUrl = (httpUrl || wsUrl?.replace(/^ws/, "http"))?.replace(
    /\/$/,
    "",
  );

  if (!backendUrl) {
    console.error("[KeepAlive] Backend URL not configured");
    return NextResponse.json(
      { error: "Backend URL not configured" },
      { status: 500 },
    );
  }

  try {
    const response = await fetch(`${backendUrl}/health`, {
      cache: "no-store",
      signal: AbortSignal.timeout(10000),
    });

    if (!response.ok) {
      throw new Error(`Backend responded with status: ${response.status}`);
    }

    const data = await response.json();

    return NextResponse.json({
      status: "success",
      message: "Backend pinged successfully",
      backendResponse: data,
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error("[KeepAlive] Ping failed:", error);
    return NextResponse.json(
      {
        status: "error",
        message: "Failed to ping backend",
        error: error instanceof Error ? error.message : String(error),
        timestamp: new Date().toISOString(),
      },
      { status: 502 },
    );
  }
}
