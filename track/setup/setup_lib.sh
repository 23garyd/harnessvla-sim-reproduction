#!/usr/bin/env bash
# Pure functions used by setup.sh; kept separate so tests can source them.

# Fail unless GPU 0 is the RTX A6000 (spec section 2: a driver
# re-enumeration must never silently move work to the TITAN X).
assert_gpu() {
    local name
    name="$(nvidia-smi --query-gpu=name --format=csv,noheader -i 0)"
    case "$name" in
        *"RTX A6000"*) echo "GPU0 OK: $name" ;;
        *) echo "FATAL: GPU 0 is '$name', expected RTX A6000" >&2; return 1 ;;
    esac
}

# verify_checkpoint <ckpt_dir> <sums_file>
# First run records checksums; later runs verify against them.
verify_checkpoint() {
    local ckpt_dir="$1" sums_file="$2"
    if [ -f "$sums_file" ]; then
        (cd "$ckpt_dir" && sha256sum --check --quiet "$sums_file") \
            && echo "checkpoint checksum OK: $ckpt_dir"
    else
        (cd "$ckpt_dir" && find . -type f -print0 | sort -z | xargs -0 sha256sum) \
            > "$sums_file"
        echo "recorded new checksums to $sums_file"
    fi
}
