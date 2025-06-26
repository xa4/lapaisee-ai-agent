import json
import os
from pathlib import Path

REQUIREMENTS_PATH = Path(__file__).resolve().parents[1] / "requirements.txt"
DATASET_PATH = Path(__file__).resolve().parents[1] / "data" / "finetune_samples.jsonl"

TRANSFORMERS_DEP = "transformers==4.36.1"


def add_transformers_dependency(req_path=REQUIREMENTS_PATH):
    if not req_path.exists():
        print(f"{req_path} not found")
        return
    lines = req_path.read_text().splitlines()
    if any(line.strip().startswith("transformers") for line in lines):
        print("Transformers dependency already present")
        return
    with req_path.open("a", encoding="utf-8") as f:
        if lines and lines[-1].strip() != "":
            f.write("\n")
        f.write("\n# Machine Learning\n" + TRANSFORMERS_DEP + "\n")
    print("Added transformers to requirements.txt")


def create_example_dataset(dataset_path=DATASET_PATH):
    dataset_path.parent.mkdir(parents=True, exist_ok=True)
    examples = [
        {
            "instruction": "Quelle est la gamme de la bière Jonquille ?",
            "response": "La Jonquille appartient à la gamme clean et se présente toujours en canettes de 44cl."
        },
        {
            "instruction": "Combien de canettes comporte un carton ?",
            "response": "Un carton de canettes contient systématiquement 12 unités."
        },
        {
            "instruction": "Comment calculer le stock total ?",
            "response": "Additionnez les unités en stock et le nombre de cartons multiplié par 12 pour obtenir le stock total."
        }
    ]
    with dataset_path.open("w", encoding="utf-8") as f:
        for item in examples:
            json.dump(item, f, ensure_ascii=False)
            f.write("\n")
    print(f"Wrote {len(examples)} examples to {dataset_path}")


if __name__ == "__main__":
    add_transformers_dependency()
    create_example_dataset()
