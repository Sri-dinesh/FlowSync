import { NextResponse } from "next/server";

import { prisma } from "@/lib/prisma";

export async function GET() {
  try {
    const models = await prisma.rLModel.findMany({
      orderBy: { createdAt: "desc" },
    });

    return NextResponse.json(models);
  } catch {
    return NextResponse.json(
      { error: "Failed to fetch models" },
      { status: 500 },
    );
  }
}
