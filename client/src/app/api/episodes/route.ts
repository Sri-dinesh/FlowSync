import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const simulationId = searchParams.get("simulationId");

    const episodes = await prisma.episode.findMany({
      where: simulationId ? { simulationId } : undefined,
      orderBy: [
        { simulationId: "desc" },
        { episodeNumber: "asc" },
      ],
      // Cap at 500 so the page doesn't try to render thousands of rows
      take: 500,
    });

    return NextResponse.json(episodes);
  } catch {
    return NextResponse.json(
      { error: "Failed to fetch episodes" },
      { status: 500 },
    );
  }
}
