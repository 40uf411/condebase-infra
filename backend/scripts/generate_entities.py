import argparse
import json
from pathlib import Path
import sys


def _ensure_backend_on_path() -> None:
    script_file = Path(__file__).resolve()
    backend_dir = script_file.parents[1]
    backend_path = str(backend_dir)
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate and normalize an entity model JSON file used by the generated "
            "business entity CRUD subsystem."
        )
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to source entity model JSON file.",
    )
    parser.add_argument(
        "--output",
        default="app/generated/entities_model.json",
        help="Output path for normalized entity model JSON (default: app/generated/entities_model.json).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    _ensure_backend_on_path()

    from app.entities import entity_model_to_dict, load_entity_model_from_dict

    input_path = Path(args.input).resolve()
    output_path = Path(args.output).resolve()

    if not input_path.exists():
        print(f"[error] input file not found: {input_path}")
        return 1

    try:
        payload = json.loads(input_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"[error] invalid JSON in {input_path}: {exc}")
        return 1

    if not isinstance(payload, dict):
        print("[error] model JSON must be an object with an 'entities' array")
        return 1

    try:
        model = load_entity_model_from_dict(payload)
    except ValueError as exc:
        print(f"[error] invalid entity model: {exc}")
        return 1

    normalized = entity_model_to_dict(model)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(normalized, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )

    entity_names = [entity["name"] for entity in normalized.get("entities", [])]
    print(f"[ok] normalized entity model written to {output_path}")
    print(f"[ok] entities ({len(entity_names)}): {', '.join(entity_names) if entity_names else '<none>'}")
    print(
        "[ok] CRUD integration is active through backend/app/api/routers/entities.py "
        "and backend/app/stores/entity_store.py"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
