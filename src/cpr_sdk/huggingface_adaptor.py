from huggingface_hub import HfFileSystem
from pathlib import Path 
from collections import defaultdict

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
    
    def get_document_content(self):
        """Yield the content of each document in the dataset."""
        for doc_id, paths in self.document_files_dict.items():
            doc_data = []
            for path in paths:
                file_data = self.fs.read_text(path)
                doc_data.append(file_data)           
            yield doc_id, doc_data

