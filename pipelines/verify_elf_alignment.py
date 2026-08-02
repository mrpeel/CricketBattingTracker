#!/usr/bin/env python3
"""
Pitch Analytix Pro — Automated ELF 16 KB Page Alignment Verification Script

Validates that all compiled/packaged arm64-v8a shared libraries (.so)
use a max-page-size of 16384 bytes (0x4000) for all PT_LOAD segments.
"""

import sys
import os
import glob
import subprocess
import struct
import zipfile

EXPECTED_ALIGNMENT = 16384  # 0x4000 bytes


def parse_elf_headers_native(path):
    """
    Direct ELF 64-bit Program Header parser.
    Reads p_align for all PT_LOAD (type 1) segments.
    """
    load_segments = []
    with open(path, "rb") as f:
        header = f.read(64)
        if len(header) < 64 or header[:4] != b"\x7fELF":
            return None
        ei_class, ei_data = header[4], header[5]
        if ei_class != 2:  # Only arm64-v8a (64-bit ELF) is evaluated
            return None
        fmt_char = "<" if ei_data == 1 else ">"
        
        e_phoff, = struct.unpack(fmt_char + "Q", header[32:40])
        e_phentsize, e_phnum = struct.unpack(fmt_char + "HH", header[54:58])
        
        f.seek(e_phoff)
        for _ in range(e_phnum):
            ph_entry = f.read(e_phentsize)
            if len(ph_entry) < 56:
                continue
            p_type, p_flags, p_offset, p_vaddr, p_paddr, p_filesz, p_memsz, p_align = struct.unpack(
                fmt_char + "IIQQQQQQ", ph_entry[:56]
            )
            if p_type == 1:  # PT_LOAD
                load_segments.append({
                    "offset": p_offset,
                    "vaddr": p_vaddr,
                    "align": p_align
                })
    return load_segments


def check_with_readelf(path):
    """Attempt verification using system readelf command if installed."""
    try:
        res = subprocess.run(["readelf", "-l", path], capture_output=True, text=True, check=True)
        lines = res.stdout.splitlines()
        load_lines = [l for l in lines if "LOAD" in l and "align" in l.lower()]
        return load_lines
    except Exception:
        return None


def verify_library(lib_path):
    filename = os.path.basename(lib_path)
    print(f"\n🔍 Inspecting: {filename}")
    print(f"   Path: {lib_path}")

    # Try readelf -l output if available
    readelf_output = check_with_readelf(lib_path)
    if readelf_output:
        print("   [readelf -l output]")
        for l in readelf_output:
            print(f"     {l.strip()}")

    # Direct ELF binary inspection
    segments = parse_elf_headers_native(lib_path)
    if not segments:
        print("   ❌ Error: Not a valid 64-bit ELF file")
        return False

    all_passed = True
    for idx, seg in enumerate(segments):
        align = seg["align"]
        hex_align = hex(align)
        status = "✅ PASS" if align >= EXPECTED_ALIGNMENT else "❌ FAIL (Non-compliant page alignment!)"
        print(f"   Segment #{idx+1} [PT_LOAD]: offset=0x{seg['offset']:x} vaddr=0x{seg['vaddr']:x} align={align} ({hex_align}) -> {status}")
        if align < EXPECTED_ALIGNMENT:
            all_passed = False

    return all_passed


def main():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    search_paths = [
        os.path.join(repo_root, "app/build/intermediates/merged_native_libs/debug/out/lib/arm64-v8a/*.so"),
        os.path.join(repo_root, "app/build/intermediates/stripped_native_libs/debug/out/lib/arm64-v8a/*.so"),
        os.path.join(repo_root, "wear/build/intermediates/merged_native_libs/debug/out/lib/arm64-v8a/*.so"),
    ]

    target_libs = []
    for pattern in search_paths:
        target_libs.extend(glob.glob(pattern))

    # Also search inside built APKs if present
    apk_paths = glob.glob(os.path.join(repo_root, "**/build/outputs/apk/**/*.apk"), recursive=True)
    temp_extract_dir = os.path.join(repo_root, "build/tmp/extracted_apk_so")
    import shutil
    shutil.rmtree(temp_extract_dir, ignore_errors=True)
    os.makedirs(temp_extract_dir, exist_ok=True)

    for apk_path in apk_paths:
        try:
            with zipfile.ZipFile(apk_path, 'r') as zip_ref:
                for member in zip_ref.namelist():
                    if member.startswith("lib/arm64-v8a/") and member.endswith(".so"):
                        extracted_file = zip_ref.extract(member, temp_extract_dir)
                        if extracted_file not in target_libs:
                            target_libs.append(extracted_file)
        except Exception as e:
            print(f"Warning: Could not extract APK {apk_path}: {e}")

    # Remove duplicates
    target_libs = sorted(list(set(target_libs)))

    if not target_libs:
        print("⚠️ No arm64-v8a .so libraries found. Build the project first (e.g. ./gradlew assembleDebug).")
        sys.exit(1)

    print(f"==================================================")
    print(f"🛡️  16 KB Page Alignment Audit (arm64-v8a binaries)")
    print(f"==================================================")
    print(f"Found {len(target_libs)} shared library targets to verify.")

    failed_libs = []
    passed_libs = []

    for lib_path in target_libs:
        if verify_library(lib_path):
            passed_libs.append(lib_path)
        else:
            failed_libs.append(lib_path)

    print("\n==================================================")
    print("📊 Audit Summary Results")
    print("==================================================")
    print(f"Passed (16 KB aligned): {len(passed_libs)}")
    print(f"Failed (4 KB aligned):  {len(failed_libs)}")

    if failed_libs:
        print("\n❌ FAILURE: The following libraries are NOT 16 KB page size aligned:")
        for f in failed_libs:
            print(f"  - {f}")
        sys.exit(1)

    print("\n🎉 SUCCESS: All arm64-v8a native libraries are strictly 16 KB (16384 bytes) page size aligned!")
    sys.exit(0)


if __name__ == "__main__":
    main()
