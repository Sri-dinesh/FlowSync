"use client";

import type { CCTVFrameData } from "@/app/realworld/page";

export default function SignalDecisionPanel({ frame }: { frame: CCTVFrameData | null }) {
  const contract = frame?.observation_contract;
  return (
    <section className="rounded-xl border border-white/10 bg-white/[0.02] overflow-hidden">
      <h2 className="px-4 py-3 border-b border-white/[0.06] text-xs uppercase tracking-wider text-white/50">
        Camera control status
      </h2>
      <div className="p-4 space-y-3 text-sm text-white/65">
        <p className="font-medium text-amber-300">Signal recommendation unavailable</p>
        <p>Vehicle detections alone do not supply the movement and signal information required by the trained controller.</p>
        {contract ? (
          <>
            <p className="font-mono text-xs">
              {contract.assigned_boxes} assigned · {contract.unassigned_boxes} unassigned · {contract.detected_boxes} detected
            </p>
            <ul className="list-disc pl-5 space-y-1 text-xs">
              {contract.missing_inputs.map((input) => <li key={input}>{input}</li>)}
            </ul>
          </>
        ) : <p className="text-xs">Waiting for the camera observation contract.</p>}
        <p className="text-xs text-white/40">This page does not operate physical traffic signals.</p>
      </div>
    </section>
  );
}
