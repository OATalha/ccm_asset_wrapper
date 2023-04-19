import re

from abc import ABC, abstractclassmethod, abstractmethod
from typing import Type, List, Dict
import maya.cmds as cmds


def simple_node_name(node):
    return node.rsplit("|")[-1].rsplit(":")[-1]


def has_same_reference(node1, node2):
    if not cmds.referenceQuery(node1, isNodeReferenced=True):
        return False
    if not cmds.referenceQuery(node2, isNodeReferenced=True):
        return False
    return cmds.referenceQuery(node1, rfn=True) == cmds.referenceQuery(
        node2, rfn=True
    )


def get_descendants_by_type(node, typ) -> List[str]:
    objects = cmds.ls(node, dag=True, type=typ, l=True) or []
    if type != "transform":
        objects = cmds.listRelatives(objects, parent=True, f=True) or []
    return objects


def get_ancestors(node):
    ancestors = []
    parents = cmds.listRelatives(node, parent=True) or []
    while parents:
        ancestors.append(parents[0])
        parents = cmds.listRelatives(parents[0], parent=True) or []
    return ancestors


def filter_from_children(node, name_pattern, typ="transform"):
    retval = []
    children = cmds.listRelatives(node, children=True, type=typ) or []
    for child in children:
        if re.match(name_pattern, child):
            retval.append(child)
    return retval


class MayaAssetFactory:

    @classmethod
    def find_assets(cls, nodes=None) -> List["MayaAsset"]:
        assets = []
        if nodes is None:
            root_transforms = cmds.ls("|*", type="transform") or []
        for rt in root_transforms:
            asset = cls.get_asset(rt)
            if asset:
                assets.append(asset)
        return assets

    @classmethod
    def get_asset(cls, obj):
        for subc in cls.asset_types().values():
            if subc.validate(obj):
                return subc(obj)

    @classmethod
    def asset_types(cls) -> Dict[str, Type["MayaAsset"]]:
        types = {}
        for subc in MayaAsset.__subclasses__():
            types[subc.asset_type] = subc
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


class MayaAsset(ABC):
    asset_type: str

    def __init__(self, root: str):
        self.root = root

    def __repr__(self):
        return f'{self.__class__.__name__}("{self.root}")'

    @abstractclassmethod
    def validate(self, node: str) -> bool:
        ...

    def get_geo(self) -> List[str]:
        return get_descendants_by_type(self.root, typ="mesh")

    def get_controls(self) -> List[str]:
        return get_descendants_by_type(self.root, typ="nurbsCurve")

    def get_joints(self) -> List[str]:
        return get_descendants_by_type(self.root, typ="joint")

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

    @classmethod
    def validate(cls, node):
        if not cmds.objectType(node) == "transform":
            return False
        children = (
            cmds.listRelatives(node, children=True, type="transform", f=True)
            or []
        )
        if not any(child.endswith("geo_grp") for child in children):
            return False
        if not any(child.endswith("ctls_grp") for child in children):
            return False
        if not any(child.endswith("rig_grp") for child in children):
            return False
        return True

    def geo_grp(self):
        return filter_from_children(self.root, ".*geo_grp")[0]

    def ctls_grp(self):
        return filter_from_children(self.root, ".*ctls_grp")[0]

    def rig_grp(self):
        return filter_from_children(self.root, "*rig_grp")[0]

    def get_geo(self) -> List[str]:
        return get_descendants_by_type(self.geo_grp(), typ="mesh")

    def get_controls(self) -> List[str]:
        return get_descendants_by_type(self.ctls_grp(), typ="mesh")

    def get_joints(self) -> List[str]:
        return get_descendants_by_type(self.rig_grp(), typ="joint")


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
