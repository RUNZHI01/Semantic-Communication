#!/usr/bin/env bash
set -euo pipefail

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

ARCH="$(uname -m)"
echo "=== BuildOtaTools: architecture=${ARCH} ==="

UHD_FLAGS="$(pkg-config --cflags --libs uhd) -pthread"

TARGETS=(
    OtaRxPersistentServer
    OtaTxPersistentServer
)

for target in "${TARGETS[@]}"; do
    echo "Compiling ${target}.cpp -> ${target}.${ARCH} (-O3 -march=native)"
    g++ -std=c++17 -O3 -march=native -Wall -Wextra \
        "${root_dir}/${target}.cpp" \
        -o "${root_dir}/${target}.${ARCH}" \
        ${UHD_FLAGS}
    ln -sf "${target}.${ARCH}" "${root_dir}/${target}"
    echo "Built ${root_dir}/${target}.${ARCH} (symlink: ${target})"
done

echo ""
echo "=== All targets built for ${ARCH} ==="
echo "Binaries: ${TARGETS[*]}"
echo "Note: Symlinks point to .${ARCH} variants. Different architectures can coexist."
