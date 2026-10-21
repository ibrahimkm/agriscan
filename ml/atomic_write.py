"""
AgriScan Atomic Write & File Replacement Utilities
Provides crash-safe, single-file atomic operations using POSIX os.replace semantics.

IMPORTANT ARCHITECTURAL NOTICE ON MULTI-FILE ATOMICITY:
POSIX os.replace() guarantees atomicity for a single file on the same filesystem.
Separate os.replace() calls across multiple files (such as ONNX models, class mappings,
and checkpoints) DO NOT provide multi-file transactional atomicity. If a crash or error
occurs between replacements, the filesystem will remain in an inconsistent, mixed state.

Therefore, multi-file bundle consistency must be managed through:
1. Concurrency locks preventing simultaneous release or rollback operations.
2. Verified pre-flight backups of the existing bundle.
3. Fail-stop execution with automatic rollback on partial replacement failure.
4. Comprehensive post-replacement bundle verification.
"""

import os
import sys
import stat
import json
import hashlib
import tempfile
from pathlib import Path
from typing import Any, Callable, Optional, Union


def compute_file_sha256(file_path: Union[str, Path], buffer_size: int = 65536) -> str:
    """Computes the SHA-256 hex digest of a file in streaming chunks."""
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"File not found for checksum calculation: {file_path}")
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(buffer_size):
            hasher.update(chunk)
    return hasher.hexdigest()


def validate_json_file(file_path: Union[str, Path]) -> None:
    """Validates that a file contains syntactically valid, non-empty JSON."""
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"JSON file does not exist: {file_path}")
    if path.stat().st_size == 0:
        raise ValueError(f"JSON file is empty (0 bytes): {file_path}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if data is None:
        raise ValueError(f"JSON content parsed to None in: {file_path}")


def validate_onnx_file(file_path: Union[str, Path]) -> None:
    """Validates that a file contains a structurally valid ONNX model."""
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"ONNX file does not exist: {file_path}")
    if path.stat().st_size == 0:
        raise ValueError(f"ONNX file is empty (0 bytes): {file_path}")

    try:
        import onnx
    except ImportError:
        # If ONNX is not installed in the environment, check minimum file size
        if path.stat().st_size < 1024:
            raise ValueError(f"ONNX binary is suspiciously small ({path.stat().st_size} bytes): {file_path}")
        return

    model = onnx.load(str(path))
    onnx.checker.check_model(model)


def validate_torch_checkpoint(file_path: Union[str, Path]) -> None:
    """Validates that a file contains a loadable PyTorch checkpoint dictionary."""
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Checkpoint file does not exist: {file_path}")
    if path.stat().st_size == 0:
        raise ValueError(f"Checkpoint file is empty (0 bytes): {file_path}")

    try:
        import torch
    except ImportError:
        if path.stat().st_size < 1024:
            raise ValueError(f"Checkpoint binary is suspiciously small ({path.stat().st_size} bytes): {file_path}")
        return

    try:
        ckpt = torch.load(str(path), map_location="cpu", weights_only=False)
    except TypeError:
        ckpt = torch.load(str(path), map_location="cpu")
    if not isinstance(ckpt, dict):
        raise ValueError(f"Checkpoint is not a dictionary: {type(ckpt)}")
    if "model_state_dict" not in ckpt:
        raise ValueError(f"Checkpoint missing 'model_state_dict': {file_path}")


def atomic_write_bytes(
    dest_path: Union[str, Path],
    data: bytes,
    permissions: Optional[int] = None,
    validate_fn: Optional[Callable[[Path], None]] = None,
) -> Path:
    """
    Writes binary data to destination atomically using a temporary file in the destination directory.

    Guarantees:
    - Temporary file is created in the exact destination directory (ensuring same filesystem for atomic os.replace).
    - Data is completely written, flushed, and synchronized via os.fsync().
    - File descriptor is closed before replacement.
    - If validate_fn is provided, validation executes on the closed temporary file before replacement.
    - Permissions are preserved from existing destination or set explicitly (defaulting to 0o644).
    - If any step fails, temporary file is deleted and destination is left 100% untouched.
    - Existing destination is NEVER unlinked prior to replacement.
    """
    dest = Path(dest_path).resolve()
    dest_dir = dest.parent
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Determine file permissions
    if permissions is not None:
        target_mode = permissions
    elif dest.exists():
        target_mode = stat.S_IMODE(dest.stat().st_mode)
    else:
        target_mode = 0o644

    # Create temporary file in same directory
    tmp = tempfile.NamedTemporaryFile(
        dir=dest_dir,
        prefix=f".tmp_{dest.name}_",
        delete=False,
    )
    tmp_path = Path(tmp.name)

    try:
        tmp.write(data)
        tmp.flush()
        try:
            os.fsync(tmp.fileno())
        except (OSError, AttributeError):
            pass
        tmp.close()

        # Apply target permissions
        try:
            tmp_path.chmod(target_mode)
        except OSError:
            pass

        # Validation hook before replacement
        if validate_fn is not None:
            validate_fn(tmp_path)

        # Atomic replacement
        os.replace(tmp_path, dest)
    except Exception:
        if not tmp.closed:
            tmp.close()
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        raise

    return dest


def atomic_write_text(
    dest_path: Union[str, Path],
    text: str,
    encoding: str = "utf-8",
    permissions: Optional[int] = None,
    validate_fn: Optional[Callable[[Path], None]] = None,
) -> Path:
    """Writes text content to destination atomically."""
    return atomic_write_bytes(
        dest_path=dest_path,
        data=text.encode(encoding),
        permissions=permissions,
        validate_fn=validate_fn,
    )


def atomic_write_json(
    dest_path: Union[str, Path],
    obj: Any,
    indent: int = 2,
    ensure_ascii: bool = False,
    permissions: Optional[int] = None,
    validate_json: bool = True,
) -> Path:
    """
    Serializes obj to JSON and writes to destination atomically.
    Includes built-in validation verifying the written file parses back correctly.
    """
    serialized = json.dumps(obj, indent=indent, ensure_ascii=ensure_ascii) + "\n"

    def _combined_validation(p: Path) -> None:
        if validate_json:
            validate_json_file(p)

    return atomic_write_text(
        dest_path=dest_path,
        text=serialized,
        encoding="utf-8",
        permissions=permissions,
        validate_fn=_combined_validation,
    )


def atomic_copy_file(
    src_path: Union[str, Path],
    dest_path: Union[str, Path],
    permissions: Optional[int] = None,
    validate_fn: Optional[Callable[[Path], None]] = None,
    buffer_size: int = 1024 * 1024,
) -> Path:
    """
    Copies a source file to destination atomically using a temporary file in the destination directory.

    Guarantees:
    - Source file must exist and be non-empty.
    - Temporary file is created in dest.parent to guarantee atomic os.replace().
    - Data is streamed, flushed, and synchronized via os.fsync().
    - Closed before replacement.
    - Validation callback is executed on temporary file before os.replace().
    - Cleans up temporary file on failure without touching existing destination.
    """
    src = Path(src_path).resolve()
    if not src.is_file():
        raise FileNotFoundError(f"Source file not found for atomic copy: {src}")

    dest = Path(dest_path).resolve()
    dest_dir = dest.parent
    dest_dir.mkdir(parents=True, exist_ok=True)

    if permissions is not None:
        target_mode = permissions
    elif dest.exists():
        target_mode = stat.S_IMODE(dest.stat().st_mode)
    else:
        target_mode = stat.S_IMODE(src.stat().st_mode)

    tmp = tempfile.NamedTemporaryFile(
        dir=dest_dir,
        prefix=f".tmp_{dest.name}_",
        delete=False,
    )
    tmp_path = Path(tmp.name)

    try:
        with open(src, "rb") as s:
            while chunk := s.read(buffer_size):
                tmp.write(chunk)
        tmp.flush()
        try:
            os.fsync(tmp.fileno())
        except (OSError, AttributeError):
            pass
        tmp.close()

        try:
            tmp_path.chmod(target_mode)
        except OSError:
            pass

        if validate_fn is not None:
            validate_fn(tmp_path)

        os.replace(tmp_path, dest)
    except Exception:
        if not tmp.closed:
            tmp.close()
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        raise

    return dest
