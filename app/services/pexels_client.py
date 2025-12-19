import os
import requests
from typing import List, Dict, Any
import random

class PexelsClient:
    """
    Client for interacting with Pexels API to fetch images.
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.pexels.com/v1"
        self.headers = {"Authorization": api_key}

    def search_images(self, query: str, per_page: int = 80, page: int = 1) -> Dict[str, Any]:
        """
        Search for images using Pexels API.

        Args:
            query: Search query
            per_page: Number of results per page (max 80)
            page: Page number

        Returns:
            Dict containing API response
        """
        url = f"{self.base_url}/search"
        params = {
            "query": query,
            "per_page": min(per_page, 80),
            "page": page
        }

        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()

    def download_image(self, url: str, filename: str, download_dir: str = "images") -> str:
        """
        Download an image from URL and save to local directory.

        Args:
            url: Image URL to download
            filename: Filename to save as
            download_dir: Directory to save images

        Returns:
            Path to downloaded image
        """
        os.makedirs(download_dir, exist_ok=True)
        filepath = os.path.join(download_dir, filename)

        response = requests.get(url)
        response.raise_for_status()

        with open(filepath, 'wb') as f:
            f.write(response.content)

        return filepath

    def get_images_for_theme(self, theme: str, min_images: int = 160, max_images: int = 240) -> List[Dict[str, Any]]:
        """
        Get random selection of images for a given theme.

        Args:
            theme: Theme to search for
            min_images: Minimum number of images to fetch
            max_images: Maximum number of images to fetch

        Returns:
            List of image data dictionaries
        """
        all_images = []
        page = 1

        # Fetch images until we have enough or hit API limits
        while len(all_images) < max_images:
            try:
                response = self.search_images(theme, per_page=80, page=page)
                photos = response.get('photos', [])

                if not photos:
                    break  # No more images available

                all_images.extend(photos)
                page += 1

                # Pexels API has rate limits, add delay if needed
                if page > 10:  # Safety limit
                    break

            except requests.RequestException:
                break

        # Randomly select between min_images and max_images, but not more than available
        max_selectable = min(max_images, len(all_images))
        if max_selectable < min_images:
            # If we don't have enough images, return all we have
            selected_images = all_images
        else:
            num_to_select = random.randint(min_images, max_selectable)
            selected_images = random.sample(all_images, num_to_select)

        return selected_images
