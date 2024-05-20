from huggingface_hub import HfFileSystem
from pathlib import Path
from collections import defaultdict
import io
import pandas as pd
import json
from typing import Union, Any, Generator

from cpr_sdk.s3 import ID_PATTERN


class HFFileGenerator:
    """A generator for yielding content from files in a hugging face dataset."""

    def __init__(self, hf_dataset: str, file_format: str = "parquet") -> None:
        self.fs = HfFileSystem()
        self.file_format = file_format
        self.dataset_path = Path("datasets", hf_dataset, "data")
        self.files = self.list_files_as_strings()
        self.document_files_dict = self.create_document_files_dict()

    def list_files_as_strings(self) -> list[str]:
        """List all files in the dataset as strings."""
        files = self.fs.ls(self.dataset_path.__str__(), detail=False)

        files_as_strings = []
        for file in files:
            if isinstance(file, dict):
                if self.file_format in file["name"]:
                    files_as_strings.append(file["name"])
            else:
                if self.file_format in file:
                    files_as_strings.append(file)

        return files_as_strings

    def create_document_files_dict(self) -> dict[str, list[str]]:
        """
        Create a dictionary with document IDs as keys and file paths as values.

        This is required as we have non/translated documents referring to the same
        document ID.
        """
        doc_paths_dict = defaultdict(list)

        for path in self.files:
            file_name = path.split("/")[-1]
            doc_id_match = ID_PATTERN.match(file_name)
            assert doc_id_match is not None, f"Document ID not found in path: {path}"
            doc_id = doc_id_match.group(0)
            doc_id_base = doc_id.split("_translated")[0]
            doc_paths_dict[doc_id_base].append(path)

        return doc_paths_dict

    def get_document_content_generator(
        self, limit: Union[int, None] = None
    ) -> Generator[tuple[str, Any], None, None]:
        """Yield the content of each document in the dataset."""
        count = 0
        for doc_id, paths in self.document_files_dict.items():
            if limit is not None and count >= limit:
                break
            count += 1

            doc_data = []
            for path in paths:
                with self.fs.open(path, "r") as f:
                    data_bytes_str = f.read()
                    assert isinstance(
                        data_bytes_str, str
                    ), f"Data is not a string: {data_bytes_str}"
                    data_file_obj = io.BytesIO(data_bytes_str.encode("utf-8"))
                    data_pandas_df: pd.DataFrame = pd.read_parquet(data_file_obj)
                    data_json_str: str = data_pandas_df.to_json(orient="records")
                    data: Any = json.loads(data_json_str)
                doc_data.append(data)

            yield doc_id, doc_data
