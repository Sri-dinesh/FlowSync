"""Discover and run the maintained research tools without starting a default job."""
import argparse
import runpy
import sys

COMMANDS = {
    "train": "training.train_policy",
    "evaluate": "evaluation.evaluate_replicates",
    "validate": "evaluation.evaluate_validation",
    "audit-training": "audits.audit_training_results",
    "audit-spatial": "audits.audit_spatial_inputs",
    "verify-spatial": "audits.verify_spatial_input_audit",
    "compare-spatial": "pilots.compare_spatial_pilot",
    "compare-temporal": "pilots.compare_temporal_pilot",
    "compare-updates": "pilots.compare_update_pressure_pilot",
    "export-paper": "evidence.build_paper_evidence",
    "export-teachers": "evidence.export_teacher_evidence",
}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(description=__doc__,
        epilog="Pass --help after a command for its options. Other tools can be run as python -m research.<package>.<module>.")
    parser.add_argument("command", choices=COMMANDS)
    if not argv or argv[0] in ("-h", "--help"):
        parser.print_help()
        return 0
    command = parser.parse_args(argv[:1]).command
    module = "research." + COMMANDS[command]
    sys.argv = [module, *argv[1:]]
    runpy.run_module(module, run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
