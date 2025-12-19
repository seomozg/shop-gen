import csv
import os
from typing import List, Dict, Any
from .theme_selector import select_random_theme
from .pexels_client import PexelsClient
from .deepseek_client import DeepSeekClient

class CatalogBuilder:
    """
    Service for building product catalogs by combining theme selection,
    image fetching, and content generation.
    """

    def __init__(self, pexels_api_key: str, deepseek_api_key: str):
        self.theme_selector = select_random_theme
        self.pexels_client = PexelsClient(pexels_api_key)
        self.deepseek_client = DeepSeekClient(deepseek_api_key)

    def build_catalog(self, output_dir: str = "output") -> str:
        """
        Build complete product catalog with images and CSV.

        Args:
            output_dir: Directory to save catalog files

        Returns:
            Path to the generated catalog directory
        """
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

        # Step 1: Select random theme
        theme = self.theme_selector()
        print(f"Selected theme: {theme}")

        # Step 2: Get images for theme
        images = self.pexels_client.get_images_for_theme(theme)
        print(f"Fetched {len(images)} images")

        if not images:
            raise ValueError("No images found for the selected theme")

        # Step 3: Generate catalog entries using batch processing (20 images per batch)
        print("Generating catalog data using batch API calls (20 images per batch)...")
        catalog_entries = []
        batch_size = 20

        for i in range(0, len(images), batch_size):
            batch_images = images[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(images) + batch_size - 1) // batch_size

            print(f"Processing batch {batch_num}/{total_batches} ({len(batch_images)} images)...")
            batch_entries = self.deepseek_client.generate_batch_catalog_entries(batch_images, theme)
            catalog_entries.extend(batch_entries)

        # Step 4: Download images
        images_dir = os.path.join(output_dir, "images")
        os.makedirs(images_dir, exist_ok=True)

        for i, image in enumerate(images, 1):
            try:
                # Download image
                image_url = image['src']['original']
                filename = f"{i}-1.jpg"
                self.pexels_client.download_image(image_url, filename, images_dir)

                if i % 10 == 0 or i == len(images):
                    print(f"Downloaded {i}/{len(images)} images")

            except Exception as e:
                print(f"Error downloading image {i}: {e}")
                continue

        # Step 4: Save CSV catalog
        csv_path = os.path.join(output_dir, "catalog.csv")
        self._save_csv_catalog(catalog_entries, csv_path)

        print(f"Catalog built successfully. {len(catalog_entries)} products created.")
        return output_dir

    def _save_csv_catalog(self, entries: List[Dict[str, Any]], filepath: str):
        """
        Save catalog entries to CSV file.

        Args:
            entries: List of catalog entry dictionaries
            filepath: Path to save CSV file
        """
        if not entries:
            return

        fieldnames = ["id", "title_en", "description_en", "category", "old-price", "new-price"]

        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(entries)

    def get_catalog_stats(self, catalog_dir: str) -> Dict[str, Any]:
        """
        Get statistics about the generated catalog.

        Args:
            catalog_dir: Path to catalog directory

        Returns:
            Dict with catalog statistics
        """
        csv_path = os.path.join(catalog_dir, "catalog.csv")
        images_dir = os.path.join(catalog_dir, "images")

        stats = {
            "total_products": 0,
            "total_images": 0,
            "csv_exists": os.path.exists(csv_path),
            "images_dir_exists": os.path.exists(images_dir)
        }

        if stats["csv_exists"]:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                stats["total_products"] = sum(1 for _ in reader)

        if stats["images_dir_exists"]:
            image_files = [f for f in os.listdir(images_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
            stats["total_images"] = len(image_files)

        return stats
