import { NextResponse } from "next/server";

import { prisma } from "@/lib/prisma";

export async function GET() {
  try {
    const simulations = await prisma.simulation.findMany({
      orderBy: { createdAt: "desc" },
      take: 20,
    });
    return NextResponse.json(simulations);
  } catch (error) {
    console.error("Failed to fetch simulations:", error);
    return NextResponse.json(
      { error: "Failed to fetch simulations" },
      { status: 500 },
    );
  }
}
