import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const simulationId = searchParams.get("simulationId");

    // If a specific simulationId is provided, return its metrics.
    // Otherwise aggregate across all simulations so Compare tab always has data.
    const metrics = await prisma.performanceMetric.findMany({
      where: simulationId ? { simulationId } : undefined,
      orderBy: { createdAt: "desc" },
      take: 100,
    });

    return NextResponse.json(metrics);
  } catch {
    return NextResponse.json(
      { error: "Failed to fetch metrics" },
      { status: 500 },
    );
  }
}
