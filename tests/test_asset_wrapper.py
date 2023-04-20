import os
import sys
import imp

import logging

from datetime import datetime

import maya.cmds as cmds

path = "/tahmed/tasks/ccm_asset_wrapper/maya/"
if path not in sys.path:
    sys.path.append(path)

import assets

imp.reload(assets)


log_dir = "/tahmed/logs/"
logger_name = "test_asset_wrapper"
base_dir = "/Volumes/data/PROJECTS_MAYA/CCMTEST/Downloads/cocomelon"


logger = logging.getLogger(logger_name)


def set_logging():
    time_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    logger_file_name = f"{logger_name}_{time_str}.log"
    log_file_name = os.path.join(log_dir, logger_name, logger_file_name)

    logger.setLevel(logging.DEBUG)
    if not os.path.exists(os.path.dirname(log_file_name)):
        os.makedirs(os.path.dirname(log_file_name))
    logfile_handler = logging.FileHandler(log_file_name)
    logger.addHandler(logfile_handler)


set_logging()


def log_assets():
    for asset in assets.MayaAssetFactory.find_assets():
        logger.info(f"Asset Found: {asset}")
        print(f"Asset Found: {asset}")


def open_file(path):
    opened = False
    try:
        if cmds.file(q=True, sn=True) != path:
            opened = True
            cmds.file(path, o=True, prompt=False, force=True)
    except:
        pass
    logger.info(f"File Opened {path}" if opened
                else f"File {path} already open")


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


def test_chars():
    logger.info("Executing test_chars")
    for char_ma in get_asset_files(asset_type="char"):
        open_file(char_ma)
        log_assets()


def test_jj():
    logger.info("Executing test_jj")
    jj = "/Volumes/data/PROJECTS_MAYA/CCMTEST/Downloads/cocomelon/assets/char/jj/jjDefault_RIG.ma"
    log_assets()


def test_props():
    logger.info("Executing test_props")
    for ma in get_asset_files(asset_type="prop"):
        open_file(ma)
        log_assets()


test_props()
