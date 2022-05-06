from uitb.perception.base import BaseModule
from uitb.utils.functions import parent_path

import numpy as np


class BasicWithEndEffectorPosition(BaseModule):

  def __init__(self, model, data, bm_model, end_effector, **kwargs):
    self.end_effector = end_effector
    super().__init__(model, data, bm_model)
    self.module_folder = parent_path(__file__)
    self.independent_joints = None

  @staticmethod
  def insert(task, config, **kwargs):
    pass

  def reset(self, model, data, rng):
    pass

  def extractor(self):
    return None

  def get_observation_space_params(self):
    return {"low": -float('inf'), "high": float('inf'), "shape": self.observation_shape}

  def get_observation(self, model, data):

    # Normalise qpos
    jnt_range = model.jnt_range[self.bm_model.independent_joints]
    qpos = data.qpos[self.bm_model.independent_joints].copy()
    qpos = qpos - jnt_range[:, 0] / (jnt_range[:, 1] - jnt_range[:, 0])
    qpos = (qpos - 0.5) * 2

    # Get qvel, qacc
    qvel = data.qvel[self.bm_model.independent_joints].copy()
    qacc = data.qacc[self.bm_model.independent_joints].copy()

    # Get end-effector position; not normalised
    fingertip_position = data.geom(self.end_effector).xpos

    # Normalise act
    act = (data.act.copy() - 0.5) * 2

    # Proprioception features
    proprioception = np.concatenate([qpos, qvel, qacc, fingertip_position, act])

    return proprioception