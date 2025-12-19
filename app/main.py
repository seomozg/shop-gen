#!/usr/bin/env python3
"""
Main entry point for the Catalog Generator Service.
"""

import os
import argparse
from dotenv import load_dotenv
from app.services.catalog_builder import CatalogBuilder
from app.services.archive_service import ArchiveService

def main():
    """
    Main function to run the catalog generation service.
    """
    # Load environment variables
    load_dotenv()

    # Get API keys from environment
    pexels_api_key = os.getenv("PEXELS_API_KEY")
    deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")

    if not pexels_api_key:
        raise ValueError("PEXELS_API_KEY environment variable is required")
    if not deepseek_api_key:
        raise ValueError("DEEPSEEK_API_KEY environment variable is required")

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Generate online store catalog")
    parser.add_argument(
        "--output-dir",
        default="catalog_output",
        help="Directory to save catalog files (default: catalog_output)"
    )
    parser.add_argument(
        "--archive-name",
        default="catalog.zip",
        help="Name of the output archive file (default: catalog.zip)"
    )

    args = parser.parse_args()

    print("🚀 Starting Catalog Generator Service")
    print(f"Output directory: {args.output_dir}")
    print(f"Archive name: {args.archive_name}")

    try:
        # Step 1: Build the catalog
        print("\n📦 Building catalog...")
        catalog_builder = CatalogBuilder(pexels_api_key, deepseek_api_key)
        catalog_dir = catalog_builder.build_catalog(args.output_dir)

        # Step 2: Create archive
        print("\n📁 Creating archive...")
        archive_service = ArchiveService()
        archive_path = archive_service.create_catalog_archive(catalog_dir, args.archive_name)

        # Step 3: Validate archive
        print("\n✅ Validating archive...")
        validation = archive_service.validate_archive(archive_path)

        if validation["valid"]:
            print(f"✅ Catalog generation completed successfully!")
            print(f"📊 Generated {validation['image_count']} products with {validation['image_count']} images")
            print(f"📁 Archive created: {archive_path}")
            print(f"📂 Catalog files: {catalog_dir}")

            # Show catalog statistics
            stats = catalog_builder.get_catalog_stats(catalog_dir)
            print(f"📈 Statistics: {stats['total_products']} products, {stats['total_images']} images")
        else:
            print(f"❌ Archive validation failed: {validation.get('error', 'Unknown error')}")
            return 1

    except Exception as e:
        print(f"❌ Error during catalog generation: {e}")
        return 1

    return 0

if __name__ == "__main__":
    exit(main())
