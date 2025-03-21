from .common import ToolsPackageBase


class AssetTools(ToolsPackageBase):
    """
    Custom Asset Tools.
    """

    def list_all_custom_assets() -> dict[str]:
        """
        List all custom assets, descripted by their category and name.
        If user wants to create scene or object, you should use custom assets first if possible.
        """
        return {
            "Vehicles": ["汽车", "飞机"],
            "Plants": ["小草", "棕榈树"],
            "Buildings": ["房子", "学校", "医院", "小屋"],
        }

    def get_asset_info(asset_name: str) -> dict[str]:
        """
        Get Asset Info, such as bound box, size, type, file path

        Args:
        - asset_name: Asset Name to Query
        """
        return {
            "asset_name": asset_name,
            "bound_box": [0, 0, 0, 10, 10, 10],
            "size": [10, 10, 10],
            "file_path": "path/to/asset.blend",
        }

    def load_asset_by_name(asset_name: str) -> dict:
        """
        Load Asset to Blender.

        Args:
        - asset_name: Asset Name to Load
        """
        return {
            "asset_name": asset_name,
            "load_status": "success",
            "location": [0, 0, 0],
            "rotation": [0, 0, 0],
            "scale": [1, 1, 1],
        }
