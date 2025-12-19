import requests
import random
import json
from typing import Dict, List, Any

class DeepSeekClient:
    """
    Client for interacting with DeepSeek API to generate product content.
    """

    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com/v1"):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

    def generate_product_content(self, alt_text: str) -> Dict[str, str]:
        """
        Generate product title and description from image alt text.

        Args:
            alt_text: Alternative text from image

        Returns:
            Dict with 'title' and 'description' keys
        """
        prompt = f"""
        Based on this image description: "{alt_text}"

        Generate a product catalog entry with:
        1. A shortened title (max 50 characters)
        2. An extended description (300-500 characters)

        Format your response as JSON:
        {{
            "title": "Shortened Title",
            "description": "Extended description here..."
        }}
        """

        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 600,
            "temperature": 0.7
        }

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()

            result = response.json()
            content = result["choices"][0]["message"]["content"]

            # Try to parse JSON response
            try:
                parsed = json.loads(content)
                return {
                    "title": parsed.get("title", alt_text[:50]),
                    "description": parsed.get("description", alt_text)
                }
            except json.JSONDecodeError:
                # Fallback: extract title and description from text
                return self._parse_text_response(content, alt_text)

        except (requests.RequestException, Exception):
            # Fallback when API is unavailable
            return self._generate_fallback_content(alt_text)

    def _parse_text_response(self, content: str, alt_text: str) -> Dict[str, str]:
        """
        Parse text response when JSON parsing fails.

        Args:
            content: Raw text response
            alt_text: Original alt text for fallback

        Returns:
            Dict with title and description
        """
        # Simple parsing - look for title and description in text
        title = alt_text[:50]  # Default to truncated alt text
        description = alt_text  # Default to alt text

        lines = content.split('\n')
        for line in lines:
            if '"title":' in line:
                title = line.split('"title":')[1].strip().strip('",')
            elif '"description":' in line:
                desc_line = line.split('"description":')[1].strip().strip('",')
                if desc_line:
                    description = desc_line

        return {"title": title, "description": description}

    def _generate_fallback_content(self, alt_text: str) -> Dict[str, str]:
        """
        Generate fallback content when API is unavailable.

        Args:
            alt_text: Original alt text

        Returns:
            Dict with title and description
        """
        # Simple fallback: use alt text truncated for title, expanded for description
        title = alt_text[:50] if len(alt_text) > 50 else alt_text

        # Expand description by repeating and adding generic text
        base_desc = alt_text
        if len(base_desc) < 300:
            expansion_text = " This high-quality product offers excellent value and is designed to meet your everyday needs. It features premium materials and craftsmanship that ensure durability and long-lasting performance. Perfect for both personal and professional use, this item combines functionality with style."
            while len(base_desc) < 400:
                base_desc += expansion_text

        description = base_desc[:500] if len(base_desc) > 500 else base_desc

        return {"title": title, "description": description}

    def generate_price(self) -> Dict[str, float]:
        """
        Generate random old and new prices with discount.

        Returns:
            Dict with 'old_price' and 'new_price' keys
        """
        old_price = round(random.uniform(100, 10000), 2)
        discount = 0.10  # 10% discount
        new_price = round(old_price * (1 - discount), 2)

        return {"old_price": old_price, "new_price": new_price}

    def generate_catalog_entry(self, alt_text: str, category: str, product_id: int) -> Dict[str, Any]:
        """
        Generate complete catalog entry for a product.

        Args:
            alt_text: Image alt text
            category: Product category
            product_id: Sequential product ID

        Returns:
            Dict with all catalog fields
        """
        content = self.generate_product_content(alt_text)
        prices = self.generate_price()

        return {
            "id": product_id,
            "title_en": content["title"],
            "description_en": content["description"],
            "category": category,
            "old-price": prices["old_price"],
            "new-price": prices["new_price"]
        }

    def generate_batch_catalog_entries(self, image_data: List[Dict[str, Any]], category: str) -> List[Dict[str, Any]]:
        """
        Generate catalog entries for multiple images in a single API call.

        Args:
            image_data: List of dicts with 'alt' key containing image alt text
            category: Product category for all images

        Returns:
            List of catalog entry dictionaries
        """
        if not image_data:
            return []

        # Prepare batch prompt - simplified version
        alt_texts = [img.get('alt', 'Product image') for img in image_data]

        prompt = f"""Create product catalog data for {len(alt_texts)} items in the {category} category.

Images:
{chr(10).join(f"{i+1}. {alt_text}" for i, alt_text in enumerate(alt_texts))}

For each image, provide a title (max 50 characters) and description (300-500 characters).

IMPORTANT: Return ONLY a valid JSON array. Do not use quotes around the array. Do not add any extra text.

Format: [{{"title": "Title 1", "description": "Description 1"}}, {{"title": "Title 2", "description": "Description 2"}}]"""

        # Allocate tokens: 600 tokens per product for title + description, plus buffer
        tokens_per_product = 600
        max_tokens = min(len(alt_texts) * tokens_per_product + 1000, 8000)  # Cap at 8000 tokens

        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": 0.7
        }



        # Increase timeout based on number of products (minimum 60 seconds, more for larger batches)
        timeout_seconds = max(60, len(alt_texts) * 10)  # 10 seconds per product, minimum 60
        print(f"🔵 Sending batch request for {len(alt_texts)} products (timeout: {timeout_seconds}s)...")

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=timeout_seconds
            )

            print(f"🟢 Response status: {response.status_code}")
            print(f"📄 Response headers: {dict(response.headers)}")

            response.raise_for_status()

            result = response.json()
            print(f"📋 Full API response: {result}")

            content = result["choices"][0]["message"]["content"]
            print(f"💬 Raw AI response content: {content[:200]}..." if len(content) > 200 else f"💬 Raw AI response content: {content}")

            # Try to parse JSON response
            print(f"🔍 Attempting to parse JSON response...")
            print(f"📝 Content type: {type(content)}")
            print(f"📏 Content length: {len(content)}")

            try:
                # Clean the content (remove potential markdown formatting)
                cleaned_content = content.strip()
                if cleaned_content.startswith('```json'):
                    cleaned_content = cleaned_content[7:]
                if cleaned_content.endswith('```'):
                    cleaned_content = cleaned_content[:-3]
                cleaned_content = cleaned_content.strip()

                print(f"🧹 Cleaned content: {cleaned_content[:200]}...")

                parsed = json.loads(cleaned_content)
                print(f"✅ JSON parsing successful! Type: {type(parsed)}, Length: {len(parsed) if isinstance(parsed, list) else 'N/A'}")

                if isinstance(parsed, list) and len(parsed) == len(alt_texts):
                    print("✅ Response format matches expected structure")
                    # Generate catalog entries with prices
                    catalog_entries = []
                    for i, content_item in enumerate(parsed):
                        prices = self.generate_price()
                        entry = {
                            "id": i + 1,
                            "title_en": content_item.get("title", alt_texts[i][:50]),
                            "description_en": content_item.get("description", alt_texts[i]),
                            "category": category,
                            "old-price": prices["old_price"],
                            "new-price": prices["new_price"]
                        }
                        catalog_entries.append(entry)
                    return catalog_entries
                else:
                    print(f"❌ Response format invalid. Expected list of {len(alt_texts)} items, got {type(parsed)} with length {len(parsed) if isinstance(parsed, list) else 'N/A'}")
                    print("Falling back to individual processing")
                    return self._generate_batch_fallback(image_data, category)

            except json.JSONDecodeError as e:
                print(f"❌ JSON parsing failed: {e}")
                print(f"❌ Raw content that failed to parse: {repr(content[:500])}")
                print("Falling back to individual processing")
                return self._generate_batch_fallback(image_data, category)

        except requests.HTTPError as e:
            print(f"🔴 HTTP Error: {e}")
            print(f"🔴 Response status: {e.response.status_code if e.response else 'Unknown'}")
            print(f"🔴 Response text: {e.response.text if e.response else 'No response'}")
            print("Falling back to individual processing")
            return self._generate_batch_fallback(image_data, category)
        except (requests.RequestException, Exception) as e:
            print(f"🔴 Request failed: {e}, falling back to individual processing")
            return self._generate_batch_fallback(image_data, category)

    def _generate_batch_fallback(self, image_data: List[Dict[str, Any]], category: str) -> List[Dict[str, Any]]:
        """
        Fallback method that generates entries individually when batch processing fails.

        Args:
            image_data: List of image data dictionaries
            category: Product category

        Returns:
            List of catalog entries
        """
        catalog_entries = []
        for i, image in enumerate(image_data, 1):
            try:
                entry = self.generate_catalog_entry(
                    image.get('alt', 'Product image'),
                    category,
                    i
                )
                catalog_entries.append(entry)
            except Exception as e:
                print(f"Error generating entry for image {i}: {e}")
                continue
        return catalog_entries
