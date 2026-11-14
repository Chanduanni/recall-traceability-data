"""Run the generator twice with the same seed; compare row counts and SHA-256 checksums."""
import hashlib
import os
import shutil
import subprocess
import sys

SEED = 20261022


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def run(tag):
    base = os.path.join("repro_check", tag)
    out, truth = os.path.join(base, "data"), os.path.join(base, "ground_truth")
    subprocess.run([sys.executable, "generate_data.py", "--seed", str(SEED),
                    "--out", out, "--truth-out", truth],
                   check=True, stdout=subprocess.DEVNULL)
    result = {}
    for folder in (out, truth):
        for name in sorted(os.listdir(folder)):
            if name.endswith(".csv"):
                path = os.path.join(folder, name)
                with open(path, newline="", encoding="utf-8") as f:
                    rows = sum(1 for _ in f) - 1
                result[name] = (rows, sha256(path))
    return result


def main():
    shutil.rmtree("repro_check", ignore_errors=True)
    print("Run 1...")
    a = run("run1")
    print("Run 2...")
    b = run("run2")

    lines = ["# Reproducibility Check", "",
             f"Generator run twice with seed {SEED}. Row counts and SHA-256 checksums compared.", "",
             "| File | Rows (run 1) | Rows (run 2) | SHA-256 run 1 | SHA-256 run 2 | Match |",
             "|---|---|---|---|---|---|"]
    same = 0
    for name in sorted(a):
        ok = a[name] == b.get(name)
        same += ok
        lines.append(f"| {name} | {a[name][0]} | {b[name][0]} | {a[name][1][:16]} | {b[name][1][:16]} | {'YES' if ok else 'NO'} |")
    verdict = "REPRODUCIBLE" if same == len(a) == len(b) else "NOT REPRODUCIBLE"
    lines += ["", f"Result: {same} of {len(a)} files identical. {verdict}"]

    with open(os.path.join("docs", "REPRODUCIBILITY.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    shutil.rmtree("repro_check", ignore_errors=True)

    print(f"Files compared: {len(a)}, identical: {same}")
    print(verdict)
    sys.exit(0 if verdict == "REPRODUCIBLE" else 1)


if __name__ == "__main__":
    main()