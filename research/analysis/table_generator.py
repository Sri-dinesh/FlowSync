"""
table_generator.py — IEEE Publication-Ready LaTeX and CSV Table Generator
==========================================================================
Converts experimental benchmark results and statistical analyses into clean
LaTeX booktabs tables and CSV summaries for IEEE T-ITS manuscripts.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, List


class TableGenerator:
    """Generates LaTeX booktabs tables and structured CSV files."""

    @staticmethod
    def generate_main_benchmark_latex(
        summary_records: List[Dict[str, Any]],
        output_path: Path | str,
        caption: str = "Comparative Evaluation Across Traffic Controllers under Paired Benchmark Conditions",
        label: str = "tab:benchmark_comparison",
    ) -> str:
        """
        Generates IEEE format table with booktabs for main controller comparison.
        """
        lines = [
            r"\begin{table*}[t]",
            r"\centering",
            rf"\caption{{{caption}}}",
            rf"\label{{{label}}}",
            r"\begin{tabular}{lcccccc}",
            r"\toprule",
            r"\textbf{Controller} & \textbf{Mean Delay (s)} & \textbf{P95 Delay (s)} & \textbf{Queue-Area (veh$\cdot$s)} & \textbf{Throughput (veh/h)} & \textbf{Fallback Rate (\%)} & \textbf{Shield Int.} \\",
            r"\midrule",
        ]

        for r in summary_records:
            name = r.get("controller", "Unknown")
            delay = f"{r.get('mean_delay', 0.0):.2f} $\\pm$ {r.get('std_delay', 0.0):.2f}"
            p95 = f"{r.get('p95_delay', 0.0):.2f}"
            qa = f"{r.get('queue_area', 0.0):.1f}"
            tp = f"{r.get('throughput', 0.0):.1f}"
            fb = f"{r.get('fallback_rate', 0.0) * 100:.1f}\\%" if "fallback_rate" in r else "--"
            shield = f"{int(r.get('shield_interventions', 0))}"

            # Bold the top performing proposed method if it's flowsync_uq
            if "flowsync_uq" in name.lower():
                name_str = f"\\textbf{{{name}}}"
                delay = f"\\textbf{{{delay}}}"
                p95 = f"\\textbf{{{p95}}}"
            else:
                name_str = name

            lines.append(f"{name_str} & {delay} & {p95} & {qa} & {tp} & {fb} & {shield} \\\\")

        lines.extend([
            r"\bottomrule",
            r"\end{tabular}",
            r"\end{table*}",
        ])

        tex_content = "\n".join(lines)
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w") as f:
            f.write(tex_content)
        return tex_content

    @staticmethod
    def generate_robustness_latex(
        robustness_data: List[Dict[str, Any]],
        output_path: Path | str,
        caption: str = "Robustness Analysis Under Controlled Perception Faults",
        label: str = "tab:robustness_eval",
    ) -> str:
        """
        Generates table showing degradation across noise conditions.
        """
        lines = [
            r"\begin{table*}[t]",
            r"\centering",
            rf"\caption{{{caption}}}",
            rf"\label{{{label}}}",
            r"\begin{tabular}{lcccccc}",
            r"\toprule",
            r"\textbf{Controller} & \textbf{Clean Delay} & \textbf{Miss 10\%} & \textbf{Miss 20\%} & \textbf{Latency 250ms} & \textbf{Combined} & \textbf{Max Degradation (\%)} \\",
            r"\midrule",
        ]

        for r in robustness_data:
            ctrl = r.get("controller", "Unknown")
            c_delay = f"{r.get('clean_delay', 0.0):.2f}"
            m10 = f"{r.get('miss_10_delay', 0.0):.2f}"
            m20 = f"{r.get('miss_20_delay', 0.0):.2f}"
            lat = f"{r.get('latency_250ms_delay', 0.0):.2f}"
            comb = f"{r.get('combined_delay', 0.0):.2f}"
            deg = f"{r.get('max_degradation_pct', 0.0):.1f}\\%"

            if "flowsync_uq" in ctrl.lower():
                lines.append(
                    f"\\textbf{{{ctrl}}} & \\textbf{{{c_delay}}} & \\textbf{{{m10}}} & "
                    f"\\textbf{{{m20}}} & \\textbf{{{lat}}} & \\textbf{{{comb}}} & \\textbf{{{deg}}} \\\\"
                )
            else:
                lines.append(f"{ctrl} & {c_delay} & {m10} & {m20} & {lat} & {comb} & {deg} \\\\")

        lines.extend([
            r"\bottomrule",
            r"\end{tabular}",
            r"\end{table*}",
        ])

        tex_content = "\n".join(lines)
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w") as f:
            f.write(tex_content)
        return tex_content

    @staticmethod
    def export_csv(records: List[Dict[str, Any]], output_path: Path | str) -> None:
        """Exports records to CSV with clean headers."""
        if not records:
            return
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        keys = list(records[0].keys())
        with open(out, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(records)
