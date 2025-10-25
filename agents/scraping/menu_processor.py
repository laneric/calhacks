"""menu processor for transforming raw scraped data into RAG-ready format."""

import json
import hashlib
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass, asdict


@dataclass
class MenuItem:
    """represents a single menu item."""

    name: str
    description: str
    price: Optional[str]
    category: Optional[str]
    dietary_info: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """convert to dictionary.

        returns:
            dict representation of menu item
        """
        return asdict(self)


@dataclass
class ProcessedMenu:
    """represents processed menu data ready for RAG."""

    restaurant_name: str
    source: str
    menu_items: List[MenuItem]
    metadata: Dict[str, Any]
    document_chunks: List[str]
    menu_hash: str

    def to_dict(self) -> Dict[str, Any]:
        """convert to dictionary.

        returns:
            dict representation of processed menu
        """
        return {
            "restaurant_name": self.restaurant_name,
            "source": self.source,
            "menu_items": [item.to_dict() for item in self.menu_items],
            "metadata": self.metadata,
            "document_chunks": self.document_chunks,
            "menu_hash": self.menu_hash
        }

    def save_to_file(self, output_dir: str) -> str:
        """save processed menu to json file.

        args:
            output_dir: directory to save the file

        returns:
            path to saved file
        """
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        safe_name = "".join(
            c if c.isalnum() else "_" for c in self.restaurant_name
        ).lower()
        filename = f"{safe_name}_{self.source}_processed.json"
        filepath = Path(output_dir) / filename

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

        return str(filepath)


class MenuProcessor:
    """processor for normalizing and chunking menu data for RAG."""

    def __init__(
        self,
        processed_data_dir: str = "data/processed/menus",
        chunk_size: int = 500
    ) -> None:
        """initialize menu processor.

        args:
            processed_data_dir: directory to store processed data
            chunk_size: target character count for document chunks
        """
        self.processed_data_dir = processed_data_dir
        self.chunk_size = chunk_size
        Path(processed_data_dir).mkdir(parents=True, exist_ok=True)

    def _extract_yelp_menu_items(
        self,
        raw_data: Dict[str, Any]
    ) -> List[MenuItem]:
        """extract menu items from yelp raw data.

        args:
            raw_data: raw data from yelp scraper

        returns:
            list of MenuItem objects
        """
        menu_items = []

        # yelp data structure may vary; handle common formats
        # typically found in raw_data['menu'] or raw_data['business']['menu']
        menu_data = raw_data.get("menu", [])
        if not menu_data and "business" in raw_data:
            menu_data = raw_data.get("business", {}).get("menu", [])

        for item in menu_data:
            if not isinstance(item, dict):
                continue

            menu_item = MenuItem(
                name=item.get("name", "").strip(),
                description=item.get("description", "").strip(),
                price=item.get("price", "").strip() or None,
                category=item.get("category", "").strip() or None,
                dietary_info=item.get("dietary_info", [])
            )

            if menu_item.name:
                menu_items.append(menu_item)

        return menu_items

    def _extract_opentable_menu_items(
        self,
        raw_data: Dict[str, Any]
    ) -> List[MenuItem]:
        """extract menu items from opentable raw data.

        args:
            raw_data: raw data from opentable scraper

        returns:
            list of MenuItem objects
        """
        menu_items = []

        # opentable structure may differ
        menu_data = raw_data.get("menu", [])
        if not menu_data and "restaurant" in raw_data:
            menu_data = raw_data.get("restaurant", {}).get("menu", [])

        for item in menu_data:
            if not isinstance(item, dict):
                continue

            menu_item = MenuItem(
                name=item.get("name", "").strip(),
                description=item.get("description", "").strip(),
                price=item.get("price", "").strip() or None,
                category=item.get("section", "").strip() or None,
                dietary_info=item.get("tags", [])
            )

            if menu_item.name:
                menu_items.append(menu_item)

        return menu_items

    def _extract_metadata(
        self,
        raw_data: Dict[str, Any],
        source: str
    ) -> Dict[str, Any]:
        """extract restaurant metadata from raw data.

        args:
            raw_data: raw scraped data
            source: data source ('yelp' or 'opentable')

        returns:
            dict containing metadata fields
        """
        metadata: Dict[str, Any] = {
            "source": source
        }

        if source == "yelp":
            metadata.update({
                "rating": raw_data.get("rating"),
                "review_count": raw_data.get("review_count"),
                "price_range": raw_data.get("price"),
                "categories": raw_data.get("categories", []),
                "phone": raw_data.get("phone"),
                "address": raw_data.get("address"),
                "website": raw_data.get("website")
            })
        elif source == "opentable":
            metadata.update({
                "rating": raw_data.get("rating"),
                "review_count": raw_data.get("review_count"),
                "price_range": raw_data.get("price_tier"),
                "cuisine": raw_data.get("cuisine"),
                "phone": raw_data.get("phone"),
                "address": raw_data.get("address")
            })

        return metadata

    def _create_document_chunks(
        self,
        restaurant_name: str,
        menu_items: List[MenuItem],
        metadata: Dict[str, Any]
    ) -> List[str]:
        """create document chunks for RAG from menu items.

        args:
            restaurant_name: name of restaurant
            menu_items: list of menu items
            metadata: restaurant metadata

        returns:
            list of text chunks suitable for RAG
        """
        chunks = []

        # create header chunk with restaurant info
        header = f"Restaurant: {restaurant_name}\n"
        if metadata.get("cuisine"):
            header += f"Cuisine: {metadata['cuisine']}\n"
        if metadata.get("price_range"):
            header += f"Price Range: {metadata['price_range']}\n"
        if metadata.get("rating"):
            header += f"Rating: {metadata['rating']}\n"

        chunks.append(header.strip())

        # group items by category
        categorized: Dict[str, List[MenuItem]] = {}
        for item in menu_items:
            category = item.category or "Other"
            if category not in categorized:
                categorized[category] = []
            categorized[category].append(item)

        # create chunks per category
        for category, items in categorized.items():
            category_chunk = f"\n{category}:\n"

            for item in items:
                item_text = f"- {item.name}"
                if item.price:
                    item_text += f" (${item.price})"
                if item.description:
                    item_text += f": {item.description}"
                if item.dietary_info:
                    item_text += f" [{', '.join(item.dietary_info)}]"
                item_text += "\n"

                # check if adding this item exceeds chunk size
                if len(category_chunk) + len(item_text) > self.chunk_size:
                    chunks.append(category_chunk.strip())
                    category_chunk = f"\n{category} (continued):\n"

                category_chunk += item_text

            if category_chunk.strip():
                chunks.append(category_chunk.strip())

        return chunks

    def _compute_menu_hash(self, menu_items: List[MenuItem]) -> str:
        """compute hash of menu items for change detection.

        args:
            menu_items: list of menu items

        returns:
            md5 hash of menu content
        """
        content = json.dumps(
            [item.to_dict() for item in menu_items],
            sort_keys=True
        )
        return hashlib.md5(content.encode()).hexdigest()

    def process_menu(
        self,
        restaurant_name: str,
        raw_data: Dict[str, Any],
        source: str
    ) -> ProcessedMenu:
        """process raw menu data into RAG-ready format.

        args:
            restaurant_name: name of restaurant
            raw_data: raw scraped data
            source: data source ('yelp' or 'opentable')

        returns:
            ProcessedMenu object with normalized data and chunks
        """
        # extract menu items based on source
        if source == "yelp":
            menu_items = self._extract_yelp_menu_items(raw_data)
        elif source == "opentable":
            menu_items = self._extract_opentable_menu_items(raw_data)
        else:
            menu_items = []

        # extract metadata
        metadata = self._extract_metadata(raw_data, source)

        # create document chunks
        chunks = self._create_document_chunks(
            restaurant_name,
            menu_items,
            metadata
        )

        # compute hash
        menu_hash = self._compute_menu_hash(menu_items)

        processed = ProcessedMenu(
            restaurant_name=restaurant_name,
            source=source,
            menu_items=menu_items,
            metadata=metadata,
            document_chunks=chunks,
            menu_hash=menu_hash
        )

        # save processed data
        processed.save_to_file(self.processed_data_dir)

        return processed

    def batch_process_menus(
        self,
        menu_data_list: List[Dict[str, Any]]
    ) -> List[ProcessedMenu]:
        """process multiple menus in batch.

        args:
            menu_data_list: list of dicts with keys:
                - restaurant_name: str
                - raw_data: Dict[str, Any]
                - source: str ('yelp' or 'opentable')

        returns:
            list of ProcessedMenu objects
        """
        processed_menus = []

        for menu_data in menu_data_list:
            try:
                processed = self.process_menu(
                    restaurant_name=menu_data["restaurant_name"],
                    raw_data=menu_data["raw_data"],
                    source=menu_data["source"]
                )
                processed_menus.append(processed)
            except Exception as e:
                print(
                    f"error processing {menu_data.get('restaurant_name')}: {e}"
                )

        return processed_menus
