import subprocess
import sys
import os

OPENAPI_SPEC = os.path.join(os.path.dirname(__file__), "openapi", "marketplace.yaml")
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "app", "generated", "models.py")


def main():
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    init_file = os.path.join(os.path.dirname(OUTPUT_FILE), "__init__.py")
    if not os.path.exists(init_file):
        with open(init_file, "w") as f:
            f.write("# Auto-generated package\n")

    cmd = [
        sys.executable, "-m", "datamodel_code_generator",
        "--input", OPENAPI_SPEC,
        "--input-file-type", "openapi",
        "--output", OUTPUT_FILE,
        "--output-model-type", "pydantic_v2.BaseModel",
        "--use-standard-collections",
        "--use-union-operator",
        "--field-constraints",
        "--snake-case-field",
        "--target-python-version", "3.11",
        "--enum-field-as-literal", "all",
    ]

    print(f"Generating models from: {OPENAPI_SPEC}")
    print(f"Output: {OUTPUT_FILE}")
    print(f"Command: {' '.join(cmd)}")

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"ERROR: {result.stderr}")
        sys.exit(1)

    print("OK: Models generated successfully!")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
