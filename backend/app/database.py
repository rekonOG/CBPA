from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import Settings


@dataclass
class DatasetRepository:
    data_file: Path

    def __post_init__(self):
        if not self.data_file.exists():
            self.data_file.write_text("{}")
        self._data = json.loads(self.data_file.read_text())

    def save_dataset(self, payload: dict[str, Any]) -> None:
        dataset_id = payload["datasetId"]
        self._data[dataset_id] = payload
        self.data_file.write_text(json.dumps(self._data, default=str, indent=2))

    def get_dataset(
        self,
        dataset_id: str | None = None,
        dataset_type: str | None = None,
    ) -> dict[str, Any] | None:
        if dataset_id:
            return self._data.get(dataset_id)
        # If no dataset_id, return the first one matching dataset_type
        for dataset in self._data.values():
            if dataset_type is None or dataset.get("datasetType") == dataset_type:
                return dataset
        return None


def initialize_repository(settings: Settings) -> tuple[None, DatasetRepository]:
    data_file = Path(settings.preprocessing_output_dir) / "datasets.json"
    data_file.parent.mkdir(parents=True, exist_ok=True)
    return None, DatasetRepository(data_file=data_file)
