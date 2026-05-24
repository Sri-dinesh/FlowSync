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

    const episodes = await prisma.episode.findMany({
      where: { simulationId },
    });

    return NextResponse.json(episodes);
  } catch {
    return NextResponse.json(
      { error: "Failed to fetch episodes" },
      { status: 500 },
    );
  }
}
