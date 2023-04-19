import os
import sys
import imp

import logging


path = "/tahmed/tasks/ccm_asset_wrapper/maya/"
if path not in sys.path:
    sys.path.append(path)


logging.getLogger("test_asset_wrapper")


import assets
imp.reload(assets)



base_dir = "/Volumes/data/PROJECTS_MAYA/CCMTEST/Downloads/cocomelon"


def get_asset_files(asset_type=None, kw=None):
    asset_dir = os.path.join(base_dir, "assets")
    for root, dirs, files in os.walk(asset_dir):
        if asset_type is not None and asset_type not in root:
            continue
        for name in files:
            _, ext = os.path.splitext(name)
            if ext.lower() not in [".ma", ".mb"]:
                continue
            ma_file = os.path.join(root, name)
            yield ma_file


def test_env():
    for asset in assets.MayaAssetFactory.find_assets():
        print('asset is', asset, type(asset))
        print('num renderable objs', len(asset.get_geo()))
        print('num controls', len(asset.get_controls()))
        print('num joints', len(asset.get_joints()))


test_env()
