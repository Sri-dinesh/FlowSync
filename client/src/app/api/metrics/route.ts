import { NextResponse } from "next/server";

import { prisma } from "@/lib/prisma";

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const simulationId = searchParams.get("simulationId");

    if (!simulationId) {
      return NextResponse.json(
        { error: "simulationId is required" },
        { status: 400 },
      );
    }

    const metrics = await prisma.performanceMetric.findMany({
      where: { simulationId },
    });

    return NextResponse.json(metrics);
  } catch {
    return NextResponse.json(
      { error: "Failed to fetch metrics" },
      { status: 500 },
    );
  }
}
