import requests
import time
import json
from hashlib import md5
from tempfile import gettempdir
from copy import deepcopy
from pathlib import Path

try:
    from .common import ToolsPackageBase
except ImportError:
    ToolsPackageBase = object  # for quick testing


class PolyhavenHelper:
    url = "https://api.polyhaven.com"
    assets_cache = {}
    tags_cache = {}
    categories_cache = {}
    files_cache = {}

    @classmethod
    def fetch_assets_by_type(cls, asset_type: str) -> dict:
        asset_list = cls.fetch_assets_by_type_ex(asset_type)
        return deepcopy(asset_list)

    @classmethod
    def fetch_assets_by_type_ex(cls, asset_type: str) -> dict:
        # 优先从本地缓存中获取(缓存时间戳判定间隔为两天)
        cache_file = Path(gettempdir()) / f"polyhaven_{asset_type}_cache.json"
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        if cache_file.exists():
            # TODO: 判定缓存时间戳
            time_stamp = cache_file.stat().st_mtime
            if time_stamp > (time.time() - 60 * 60 * 24 * 2):
                if asset_type not in cls.assets_cache:
                    with open(cache_file, "r") as f:
                        data = json.load(f)
                        cls.assets_cache[asset_type] = data
                return cls.assets_cache[asset_type]
        try:
            response = requests.get(f"{cls.url}/assets?t={asset_type}")
            response.raise_for_status()
            json_data = response.json()
            cache_file.write_text(json.dumps(json_data))
            cls.assets_cache[asset_type] = json_data
            return json_data
        except requests.exceptions.RequestException as e:
            print(f"Error fetching assets: {e}")
            return {}

    @classmethod
    def fetch_tags(cls, asset_type: str) -> dict:
        if asset_type not in cls.tags_cache:
            assets_list = cls.fetch_assets_by_type(asset_type)
            tags = set()
            for asset in assets_list.values():
                tags.update(asset["tags"])
            cls.tags_cache[asset_type] = tags
        return cls.tags_cache[asset_type]  # models: 848

    @classmethod
    def fetch_categories(cls, asset_type: str) -> dict:
        if asset_type not in cls.categories_cache:
            assets_list = cls.fetch_assets_by_type(asset_type)
            categories = set()
            for asset in assets_list.values():
                categories.update(asset["categories"])
            cls.categories_cache[asset_type] = categories
        return cls.categories_cache[asset_type]  # models: 40

    @classmethod
    def fetch_model_files(cls, asset_id: str, expected_resolution: str = "1k") -> dict:
        if asset_id not in cls.files_cache:
            try:
                response = requests.get(f"{cls.url}/files/{asset_id}")
                json_data = response.json()
                config = json_data.get("blend", {})
                cls.files_cache[asset_id] = config
            except Exception:
                return {}

        last_suport_resolution = "1k"
        for resolution in sorted(cls.files_cache[asset_id].keys()):
            if resolution <= expected_resolution:
                last_suport_resolution = resolution
        files = cls.files_cache[asset_id][last_suport_resolution].get("blend", {})
        return files

    @classmethod
    def download_file(cls, url: str, name: str, size: int, file_path: str, md5_hash: str = None) -> str:
        if Path(file_path).exists():
            print(f"{name} already exists at {file_path}")
            return file_path
        # 下载文件
        print(f"Downloading {name} from {url}")
        response = requests.get(url, stream=True)
        data = b""
        # 百分比 进度条
        for chunk in response.iter_content(chunk_size=1024):
            if not chunk:
                break
            data += chunk
            print(f"\rDownloading {name} ({len(data)}/{size} bytes)", end="")
        print(f"\nDownload {name} complete")
        # 检查文件MD5
        print(f"Checking MD5 hash for {name}")
        file_md5 = md5(data).hexdigest()
        if file_md5 != md5_hash:
            print(f"MD5 hash mismatch for {name}")
            return ""
        print(f"Saving {name} to {file_path}")
        with open(file_path, "wb") as f:
            f.write(data)
        return file_path

    @classmethod
    def download_model_files(cls, asset_id: str, expected_resolution: str = "1k") -> dict:
        files = cls.fetch_model_files(asset_id, expected_resolution)
        if not files:
            return {}
        blend_cache_dir = Path(gettempdir()) / f"polyhaven_models/{asset_id}"
        blend_cache_dir.mkdir(parents=True, exist_ok=True)
        blend_cache_path = blend_cache_dir.joinpath(f"{asset_id}.blend").as_posix()
        url = files["url"]
        size = int(files["size"])
        md5_hash = files["md5"]
        blend_file = cls.download_file(url, asset_id, size, blend_cache_path, md5_hash)
        out_files = {
            "blend": blend_file,
        }

        included_files: dict = files.get("include", {})
        for file_name, info in included_files.items():
            # 'textures/Armchair_01_nor_gl_4k.exr'
            if not file_name.startswith("textures/"):
                print(f"Skipping file {file_name} as it is not in the textures folder.")
                continue
            save_path = blend_cache_dir.joinpath(file_name)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            url = info["url"]
            size = int(info["size"])
            md5_hash = info["md5"]
            texture_file = cls.download_file(url, file_name, size, save_path.as_posix(), md5_hash)
            out_files[file_name] = texture_file
        return out_files


class PolyhavenTools(ToolsPackageBase):
    """
    Polyhaven tools. Use the api to download assets.(For commercial use see https://polyhaven.com/our-api)
    """

    # def polyhaven_list_assets(asset_type: str) -> list:
    #     """
    #     List all assets of a given type.

    #     Args:
    #     - asset_type: The type of asset to list. Can be "models", "texture", or "hdri".
    #     """
    #     if asset_type not in ["models", "texture", "hdri"]:
    #         raise ValueError("Invalid asset type. Must be 'model', 'texture', or 'hdri'.")
    #     assets_list = PolyhavenHelper.fetch_assets_by_type(asset_type)
    #     for asset in assets_list.values():
    #         asset.pop("date_published", "")
    #         asset.pop("type", "")
    #         asset.pop("authors", "")
    #         asset.pop("files_hash", "")
    #         asset.pop("sponsors", "")
    #         asset.pop("polycount", "")
    #         asset.pop("texel_density", "")
    #         asset.pop("download_count", "")
    #         asset.pop("thumbnail_url", "")
    #         asset["bound_box"] = asset.pop("dimensions")
    #         asset["supported_resolutions"] = []
    #         # supported_resolutions = ["1k", "2k", "4k", "8k"]
    #         max_resolution = asset.pop("max_resolution")
    #         if isinstance(max_resolution, list):
    #             max_resolution = min(max_resolution)
    #         if max_resolution >= 1024:
    #             asset["supported_resolutions"].append("1k")
    #         if max_resolution >= 2048:
    #             asset["supported_resolutions"].append("2k")
    #         if max_resolution >= 4096:
    #             asset["supported_resolutions"].append("4k")
    #         if max_resolution >= 8192:
    #             asset["supported_resolutions"].append("8k")

    #     {
    #         "name": "Arm Chair 01",
    #         "categories": ["furniture", "seating"],
    #         "tags": ["gothic", "vintage", "chair", "furniture", "victorian", "couch", "wood", "varnished", "classic"],
    #         "max_resolution": [4096, 4096],
    #         "dimensions": [848.4309017658234, 765.7602727413177, 1065.087635157397],
    #         # "date_published": 1585605600,
    #         # "type": 2,
    #         # "authors": {"Kirill Sannikov": "All"},
    #         # "files_hash": "d47080c2004a8b2a222ee7edca7a458dc0cbbecb",
    #         # "sponsors": ["66627515", "4047949"],
    #         # "polycount": 5626,
    #         # "texel_density": 1972.3631956341671,
    #         # "download_count": 26610,
    #         # "thumbnail_url": "https://cdn.polyhaven.com/asset_img/thumbs/ArmChair_01.png?width=256&height=256",
    #     }
    #     return assets_list

    def polyhaven_search_models(names: list[str] = None, tags: list[str] = None, categories: list[str] = None) -> dict:
        """
        Search Polyhaven Online Asset Library for models. If you want to use polyhaven asset, you should search first, then try to fetch it, unless user specifies the name.

        Args:
        - names: The names of the models to search for.
        - tags: The tags of the models to search for.
        - categories: The categories of the models to search for.

        Returns:
        - A dictionary containing the results of the search.
        """

        assets_list = PolyhavenHelper.fetch_assets_by_type("models")
        names = names or []
        tags = tags or []
        categories = categories or []
        results = {
            "names_query": {
                "query": names,
                "results": [],
            },
            "tags_query": {
                "query": tags,
                "results": [],
            },
            "categories_query": {
                "query": categories,
                "results": [],
            },
        }

        for search_name in names:
            query = search_name.lower()
            for name, asset in assets_list.items():
                if query in asset["name"].lower():
                    results["names_query"]["results"].append(name)
        for search_tag in tags:
            query = search_tag.lower()
            for name, asset in assets_list.items():
                if query in asset["tags"]:
                    results["tags_query"]["results"].append(name)
        for search_category in categories:
            query = search_category.lower()
            for name, asset in assets_list.items():
                if query in asset["categories"]:
                    results["categories_query"]["results"].append(name)
        if not names:
            results.pop("names_query")
        if not tags:
            results.pop("tags_query")
        if not categories:
            results.pop("categories_query")
        return results

    def polyhaven_fetch_model_info(asset_id: str) -> dict:
        """
        Before you use model asset, use this function to get model info then determint how or whether to use it.

        Args:
        - asset_id: The id of the asset info to fetch.
        """
        assets_list = PolyhavenHelper.fetch_assets_by_type("models")
        asset = assets_list.get(asset_id)
        if not asset:
            raise ValueError(f"Asset with id {asset_id} not found")
        asset.pop("date_published", "")
        asset.pop("type", "")
        asset.pop("authors", "")
        asset.pop("files_hash", "")
        asset.pop("sponsors", "")
        asset.pop("polycount", "")
        asset.pop("texel_density", "")
        asset.pop("download_count", "")
        asset.pop("thumbnail_url", "")
        asset["bound_box"] = asset.pop("dimensions")
        asset["supported_resolutions"] = []
        # supported_resolutions = ["1k", "2k", "4k", "8k"]
        max_resolution = asset.pop("max_resolution")
        if isinstance(max_resolution, list):
            max_resolution = min(max_resolution)
        if max_resolution >= 1024:
            asset["supported_resolutions"].append("1k")
        if max_resolution >= 2048:
            asset["supported_resolutions"].append("2k")
        if max_resolution >= 4096:
            asset["supported_resolutions"].append("4k")
        if max_resolution >= 8192:
            asset["supported_resolutions"].append("8k")
        {
            "name": "Arm Chair 01",
            "categories": ["furniture", "seating"],
            "tags": ["gothic", "vintage", "chair", "furniture", "victorian", "couch", "wood", "varnished", "classic"],
            "max_resolution": [4096, 4096],
            "dimensions": [848.4309017658234, 765.7602727413177, 1065.087635157397],
            # "date_published": 1585605600,
            # "type": 2,
            # "authors": {"Kirill Sannikov": "All"},
            # "files_hash": "d47080c2004a8b2a222ee7edca7a458dc0cbbecb",
            # "sponsors": ["66627515", "4047949"],
            # "polycount": 5626,
            # "texel_density": 1972.3631956341671,
            # "download_count": 26610,
            # "thumbnail_url": "https://cdn.polyhaven.com/asset_img/thumbs/ArmChair_01.png?width=256&height=256",
        }
        return asset

    def polyhaven_use_model_asset(asset_id: str, expected_resolution: str = "1k") -> dict:
        """
        If you choose one model from the search results, you can use this tool to load it into scene.

        Args:
        - asset_id: The asset id of the model you want to use.
        - expected_resolution: The expected resolution of the model. Can be "1k", "2k", "4k", or "8k".
        """
        files = PolyhavenHelper.download_model_files(asset_id, expected_resolution)
        {
            "blend": "xxx/ArmChair_01.blend",
            "textures/Armchair_01_diff_1k.jpg": "xxx/ArmChair_01/textures/Armchair_01_diff_1k.jpg",
            "textures/Armchair_01_metallic_1k.exr": "xxx/ArmChair_01/textures/Armchair_01_metallic_1k.exr",
            "textures/Armchair_01_nor_gl_1k.exr": "xxx/ArmChair_01/textures/Armchair_01_nor_gl_1k.exr",
            "textures/Armchair_01_roughness_1k.jpg": "xxx/ArmChair_01/textures/Armchair_01_roughness_1k.jpg",
        }
        if "blend" not in files:
            raise ValueError("No blend file found for asset id: " + asset_id)

        blend_file_path = files["blend"]
        loaded_object_names = []
        import bpy

        old_objects = set(bpy.data.objects)

        with bpy.data.libraries.load(blend_file_path) as (data_from, data_to):
            loaded_object_names = list(data_from.objects)
            data_to.objects = data_from.objects

        new_objects = set(bpy.data.objects) - old_objects
        for obj in new_objects:
            bpy.context.collection.objects.link(obj)
        return {
            "loaded_asset_id": asset_id,
            "resolution": expected_resolution,
            "loaded_objects": loaded_object_names,
        }

    # TODO
    # def polyhaven_get_all_tags(asset_type: str) -> list:
    #     assets_list = PolyhavenHelper.fetch_assets_by_type(asset_type)
    #     tags = set()
    #     for asset in assets_list.values():
    #         tags.update(asset["tags"])
    #     return list(tags)  # models: 848

    # def polyhaven_get_all_categories(asset_type: str) -> list:
    #     assets_list = PolyhavenHelper.fetch_assets_by_type(asset_type)
    #     categories = set()
    #     for asset in assets_list.values():
    #         categories.update(asset["categories"])
    #     return list(categories)  # models: 40
