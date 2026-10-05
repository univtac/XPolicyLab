"""Expose the existing UniVTAC tactile ACT policy through XPolicyLab."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import torch
import yaml
from torchvision import transforms

from XPolicyLab.model_template import ModelTemplate

# ``setup_policy_server.py`` puts the XPolicyLab checkout itself at the front
# of ``sys.path``; make the UniVTAC policy package win the ambiguous top-level
# name before importing the original ACT implementation.
_univtac_root = os.environ.get("UNIVTAC_ROOT") or str(Path(__file__).resolve().parents[4])
if _univtac_root:
    _act_root = str(Path(_univtac_root) / "policy" / "ACT")
    if _act_root not in sys.path:
        sys.path.insert(0, _act_root)
# Import as a top-level module: XPolicyLab also owns a regular ``policy``
# package, so importing ``policy.ACT`` would resolve to the wrong checkout.
from act_policy import ACT


class Model(ModelTemplate):
    def __init__(self, model_cfg):
        cfg = dict(model_cfg)
        cfg.setdefault("task_name", "sim-grasp_classify-grasp_parallel-1")
        cfg.setdefault("seed", 0)
        cfg.setdefault("num_epochs", 1)
        self.device = torch.device(cfg.get("device", "cuda:0"))
        self.camera_names = list(cfg.get("camera_names", ["cam_head"]))
        # These are XPolicyLab vision keys.  The wrapped ACT implementation
        # may use its historical ``tac_left``/``tac_right`` names.
        self.protocol_tactile_names = list(cfg.get("tactile_names", ["cam_tactile_left", "cam_tactile_right"]))
        self._camera_transform = transforms.Compose([
            transforms.ToPILImage(), transforms.Resize((256, 256)), transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
        self._tactile_transform = transforms.Compose([
            transforms.ToPILImage(), transforms.Resize((256, 256)), transforms.ToTensor(),
        ])
        ckpt_dir = cfg.get("ckpt_dir")
        if ckpt_dir and not os.path.isabs(ckpt_dir):
            root = os.environ.get("UNIVTAC_ROOT")
            if root:
                cfg["ckpt_dir"] = str(Path(root) / ckpt_dir)
        if cfg.get("ckpt_dir"):
            config_path = Path(cfg["ckpt_dir"]) / "model_config.yaml"
            if config_path.exists():
                trained_cfg = yaml.safe_load(config_path.read_text()) or {}
                trained_cfg.update({"ckpt_dir": cfg["ckpt_dir"], "device": cfg.get("device", "cuda:0")})
                cfg = trained_cfg
        self.act_tactile_names = list(cfg.get("tactile_names", ["tac_left", "tac_right"]))
        self.model = ACT(cfg)

    @staticmethod
    def _image(obs, name):
        try:
            return obs["vision"][name]["color"]
        except KeyError as exc:
            raise ValueError(f"missing XPolicyLab vision input {name!r}") from exc

    def update_obs(self, obs):
        cams = [self._camera_transform(self._image(obs, name)) for name in self.camera_names]
        tactile = [self._tactile_transform(self._image(obs, name)) for name in self.protocol_tactile_names]
        state = np.asarray(obs["state"]["joint_state"], dtype=np.float32).reshape(-1)
        gripper = np.asarray(obs["state"].get("ee_joint_state", []), dtype=np.float32).reshape(-1)
        if state.size != 7 or gripper.size != 1:
            raise ValueError(f"expected 7 arm joints + 1 gripper joint, got {state.shape}, {gripper.shape}")
        self._obs = {
            "qpos": np.concatenate([state, gripper]),
            **{name: image for name, image in zip(self.camera_names, cams)},
            **{name: image for name, image in zip(self.act_tactile_names, tactile)},
        }

    def get_action(self):
        if not hasattr(self, "_obs") or self._obs is None:
            raise RuntimeError("update_obs must be called before get_action")
        action = np.asarray(self.model.get_action(self._obs), dtype=np.float32).reshape(-1)
        if action.size < 8:
            raise ValueError(f"ACT returned {action.size} action values; expected 8")
        return [{"joint_state": action[:7].tolist(), "ee_joint_state": action[7:8].tolist()}]

    def reset(self):
        self.model.reset()
        self._obs = None
