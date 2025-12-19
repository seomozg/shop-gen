import zipfile
import os
from typing import List, Optional

class ArchiveService:
    """
    Service for creating ZIP archives of catalog data.
    """

    def create_catalog_archive(self, source_dir: str, archive_name: str = "catalog.zip") -> str:
        """
        Create a ZIP archive containing the catalog CSV and images.

        Args:
            source_dir: Directory containing catalog files
            archive_name: Name of the output archive file

        Returns:
            Path to the created archive file

        Raises:
            ValueError: If required files are missing
        """
        if not os.path.exists(source_dir):
            raise ValueError(f"Source directory does not exist: {source_dir}")

        csv_path = os.path.join(source_dir, "catalog.csv")
        images_dir = os.path.join(source_dir, "images")

        if not os.path.exists(csv_path):
            raise ValueError("catalog.csv not found in source directory")

        if not os.path.exists(images_dir):
            raise ValueError("images directory not found in source directory")

        # Create archive
        archive_path = os.path.join(os.path.dirname(source_dir), archive_name)

        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add CSV file
            zipf.write(csv_path, "catalog.csv")

            # Add all images
            for root, dirs, files in os.walk(images_dir):
                for file in files:
                    if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                        file_path = os.path.join(root, file)
                        # Keep the images/ directory structure in the archive
                        arcname = os.path.join("images", file)
                        zipf.write(file_path, arcname)

        return archive_path

    def validate_archive(self, archive_path: str) -> dict:
        """
        Validate the contents of a catalog archive.

        Args:
            archive_path: Path to the archive file

        Returns:
            Dict with validation results
        """
        if not os.path.exists(archive_path):
            return {"valid": False, "error": "Archive file does not exist"}

        try:
            with zipfile.ZipFile(archive_path, 'r') as zipf:
                file_list = zipf.namelist()

                has_csv = "catalog.csv" in file_list
                image_files = [f for f in file_list if f.startswith("images/") and f.lower().endswith(('.jpg', '.jpeg', '.png'))]

                return {
                    "valid": has_csv and len(image_files) > 0,
                    "has_csv": has_csv,
                    "image_count": len(image_files),
                    "total_files": len(file_list),
                    "file_list": file_list[:10]  # First 10 files for preview
                }
        except zipfile.BadZipFile:
            return {"valid": False, "error": "Invalid ZIP file"}
        except Exception as e:
            return {"valid": False, "error": str(e)}

    def extract_archive(self, archive_path: str, extract_to: str) -> str:
        """
        Extract archive contents to a directory.

        Args:
            archive_path: Path to the archive file
            extract_to: Directory to extract to

        Returns:
            Path to extraction directory

        Raises:
            ValueError: If archive is invalid
        """
        os.makedirs(extract_to, exist_ok=True)

        try:
            with zipfile.ZipFile(archive_path, 'r') as zipf:
                zipf.extractall(extract_to)
            return extract_to
        except zipfile.BadZipFile:
            raise ValueError("Invalid ZIP file")
        except Exception as e:
            raise ValueError(f"Failed to extract archive: {e}")
