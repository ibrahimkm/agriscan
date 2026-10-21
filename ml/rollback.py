"""
AgriScan Model Rollback CLI Utility
Convenience entry point for listing, validating, and restoring prior release bundles.
"""

import sys
import argparse
from pathlib import Path

# Add ml and project root to sys.path
_ml_dir = Path(__file__).resolve().parent
_proj_root = _ml_dir.parent
for p in [str(_ml_dir), str(_proj_root)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from ml.promotion import ModelRollback, ReleaseBundleConfig


def main():
    parser = argparse.ArgumentParser(description="AgriScan Model Release Rollback Utility")
    parser.add_argument("--backup-dir", type=str, default=None, help="Path to backup directory to restore")
    parser.add_argument("--list", action="store_true", help="List all available validated backups")
    parser.add_argument(
        "--no-dry-run",
        action="store_true",
        default=False,
        help="Execute actual rollback restoration (Default is dry-run validation only)",
    )
    parser.add_argument(
        "--confirm-backup-id",
        type=str,
        default=None,
        help="Explicit backup ID confirmation required when executing rollback",
    )
    args = parser.parse_args()

    engine = ModelRollback()

    if args.list:
        backups = engine.list_backups()
        if not backups:
            print("[Rollback] No backups found in backup directory.")
            return
        print(f"\n[Rollback] Found {len(backups)} available backup release(s):")
        for b in backups:
            print(f"  - Backup ID: {b['backup_id']}")
            print(f"    Date:      {b['created_at']}")
            print(f"    Reason:    {b['reason']}")
            print(f"    Path:      {b['path']}")
            print(f"    Artifacts: {b['artifacts_count']}\n")
        return

    if not args.backup_dir:
        print("[Rollback] Error: You must supply --backup-dir <path> or use --list.")
        sys.exit(1)

    engine.restore_backup(
        backup_dir=Path(args.backup_dir),
        dry_run=not args.no_dry_run,
        confirm_backup_id=args.confirm_backup_id,
    )


if __name__ == "__main__":
    main()
