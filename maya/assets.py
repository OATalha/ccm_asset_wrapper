import re
import os

from abc import ABC, abstractclassmethod
from typing import Type, List, Dict
import maya.cmds as cmds


def simple_node_name(node):
    return node.rsplit("|")[-1].rsplit(":")[-1]


def has_same_reference(node1, node2):
    node1_is_ref = cmds.referenceQuery(node1, isNodeReferenced=True)
    node2_is_ref = cmds.referenceQuery(node2, isNodeReferenced=True)

    if not (node1_is_ref or node2_is_ref):
        return True

    if not (node1_is_ref and node2_is_ref):
        return False

    return cmds.referenceQuery(node1, rfn=True) == cmds.referenceQuery(
        node2, rfn=True
    )


def get_descendants_by_type(node, typ) -> List[str]:
    objects = cmds.ls(node, dag=True, type=typ, l=True) or []
    if type != "transform":
        objects = (
            cmds.listRelatives(objects, parent=True, type="transform", f=True)
            or []
        )
    return objects


def get_ancestors(node):
    ancestors = []
    long_name = cmds.ls(node, l=True) or []
    parent = long_name[0].rsplit("|", 1)[0] if long_name else ""
    while parent:
        ancestors.append(parent)
        parent = parent.rsplit("|", 1)[0]
    return ancestors


def filter_from_children(node, name_pattern=".*", typ="transform"):
    retval = []
    children = cmds.listRelatives(node, children=True, type=typ, f=True) or []
    for child in children:
        if re.match(name_pattern, child):
            retval.append(child)
    return retval


class MayaAssetFactory:
    @classmethod
    def find_assets(cls, include_ref=False) -> List["MayaAsset"]:
        assert not include_ref, "include ref is not supported at this time"
        assets = []
        nodes = cmds.ls("|*", type="transform", l=True) or []
        for rt in nodes:
            asset = cls.get_asset(rt)
            if asset:
                assets.append(asset)
        return assets

    @classmethod
    def get_asset(cls, obj, path=None):
        if path is None:
            path = cmds.file(q=True, sn=True)
        asset_cls = cls.get_asset_cls_from_path(path)
        if asset_cls:
            asset_types = [asset_cls, GenericAsset]
        else:
            asset_types = cls.asset_types()
        for subc in asset_types:
            if subc.validate(obj):
                return subc(obj)

    @classmethod
    def asset_types(cls) -> List[Type["MayaAsset"]]:
        types = []
        for subc in MayaAsset.__subclasses__():
            if subc.asset_type:
                types.append(subc)
        return types

    @classmethod
    def get_assets_from_selection(cls):
        selected = cmds.ls(sl=True, objects=True, l=True)
        roots = []

        for obj in selected:
            is_referenced = cmds.referenceQuery(obj, isNodeReferenced=True)
            ancestors = get_ancestors(obj)

            if not is_referenced:
                roots.append(ancestors[-1])
                continue
            root = obj

            for anc in ancestors:
                if not has_same_reference(obj, anc):
                    break
                root = anc
            roots.append(root)

        assets = []
        for root in roots:
            asset = cls.get_asset(root)
            assets.append(asset)

        return assets

    @classmethod
    def get_asset_cls_from_path(cls, path):
        path = os.path.normpath(path)
        for asset_cls in cls.asset_types():
            asset_type = asset_cls.asset_type
            if asset_type == "unknown":
                continue
            asset_type_re = rf"{os.path.sep}{asset_type}{os.path.sep}"
            if re.findall(asset_type_re, asset_type):
                return asset_cls


class MayaAsset(ABC):
    asset_type: str

    def __init__(self, root: str):
        self.root = root
        self.auxiliary_roots = []

    def __repr__(self):
        return f'{self.__class__.__name__}("{self.root}")'

    @abstractclassmethod
    def validate(self, node: str) -> bool:
        ...

    def add_auxiliary_root(self, obj):
        if obj not in self.auxiliary_roots:
            self.auxiliary_roots.append(obj)

    def get_geo(self) -> List[str]:
        geos = get_descendants_by_type(self.root, typ="mesh")
        for root in self.auxiliary_roots:
            geos.extend(get_descendants_by_type(root, typ="mesh"))
        return geo

    def get_controls(self) -> List[str]:
        controls = get_descendants_by_type(self.root, typ="nurbsCurve")
        for root in self.auxiliary_roots:
            controls.extend(get_descendants_by_type(root, typ="nurbsCurve"))
        return controls

    def get_joints(self) -> List[str]:
        joints = get_descendants_by_type(self.root, typ="joint")
        for root in self.auxiliary_roots:
            joints.extend(get_descendants_by_type(root, typ="joint"))
        return joints

    def is_referenced(self) -> bool:
        return cmds.referenceQuery(  # type: ignore
            self.root, isNodeReferenced=True
        )

    def namespace(self) -> bool:
        return cmds.referenceQuery(  # type: ignore
            self.root, showNamespace=True
        )

    def filename(self) -> str:
        if self.is_referenced():
            return cmds.referenceQuery(
                self.root, filename=True
            )  # type: ignore
        return cmds.file(q=True, sceneName=True)  # type: ignore


class CharacterAsset(MayaAsset):
    asset_type = "char"

    geo_re = "(?i)geo_grp"
    ctls_re = "(?i)ctls_grp"
    rig_re = "(?i)rig_grp"

    root_ctrl_re = "TSM3_root"

    @classmethod
    def validate(cls, node):
        if not cmds.objectType(node) == "transform":
            return False
        children = (
            cmds.listRelatives(node, children=True, type="transform", f=True)
            or []
        )
        if not any(
            re.match(cls.geo_re, simple_node_name(child)) for child in children
        ):
            return False
        return True

    def geo_grp(self):
        return filter_from_children(self.root, self.geo_re)[0]

    def ctls_grp(self):
        filtered = filter_from_children(self.root, self.ctls_re)[0]
        if filtered:
            return filtered[0]

    def rig_grp(self):
        filtered = filter_from_children(self.root, self.rig_re)[0]
        if filtered:
            return filtered[0]

    def get_geo(self) -> List[str]:
        return get_descendants_by_type(self.geo_grp(), typ="mesh")

    def get_controls(self) -> List[str]:
        controls = []
        ctls_grp = self.ctls_grp()
        if ctls_grp:
            controls = get_descendants_by_type(ctls_grp, typ="mesh")
        return controls

    def get_joints(self) -> List[str]:
        joints = []
        rig_grp = self.rig_grp()
        if rig_grp:
            joints = get_descendants_by_type(rig_grp, typ="joint")
        return joints


class PropAsset(MayaAsset):
    asset_type = "prop"
    name_re = r"(?i)(.*)_glbl\d?$"

    @classmethod
    def validate(cls, node: str):
        if not cmds.objectType(node) == "transform":
            return False
        if not cmds.listRelatives(
            children=True, shapes=True, ni=True, type="nurbsCurve"
        ):
            return False
        node_name = simple_node_name(node)
        if not re.match(cls.name_re, node_name):
            return False
        return True


class EnvironmentAsset(MayaAsset):
    asset_type = "envr"
    name_re = "ENV_grp"

    @classmethod
    def validate(cls, node: str):
        if not cmds.objectType(node) == "transform":
            return False
        if cmds.listRelatives(children=True, shapes=True):
            return False
        node_name = simple_node_name(node)
        if not re.match(cls.name_re, node_name):
            return False
        return True


class GenericAsset(MayaAsset):
    asset_type = "unknown"
    name_re = "(?i)(.*_grp|.*root)"

    @classmethod
    def validate(cls, node: str):
        return cmds.objectType(node) == "transform" and re.match(
            cls.name_re, simple_node_name(node)
        )


class VehicleAsset(MayaAsset):
    asset_type = "vhcl"

    @classmethod
    def validate(cls, node: str):
        return False
