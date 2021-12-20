import gym
import os
import torch
import numpy as np
from platform import uname

from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import SubprocVecEnv
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.callbacks import CheckpointCallback

from UIB.sb3_additions.schedule import linear_schedule
from UIB.sb3_additions.policies import ActorCriticPolicy
from UIB.sb3_additions.callbacks import LinearStdDecayCallback

def generate_random_trajectories(env, num_trajectories=1_000, trajectory_length_seconds=10):

  def add_noise(actions, rate, scale):
    return np.random.normal(loc=rate*actions, scale=scale)

  # Vary noise scale and noise rate
  std_limits = [2, 4]
  timescale_limits = [0.5, 4]

  # Ignore first states cause they all start from the default pose
  ignore_first_seconds = 5
  assert trajectory_length_seconds > ignore_first_seconds, \
    f"Trajectory must be longer than {ignore_first_seconds} seconds"
  ignore_first = int(ignore_first_seconds/env.dt)

  # Trajectory length in steps
  trajectory_length = int(trajectory_length_seconds/env.dt)

  # Collect states
  states = np.zeros((num_trajectories, trajectory_length, len(env.independent_joints)))

  for trajectory_idx in range(num_trajectories):

    env.reset()
    env.render()

    # Sample noise statistics, different for each episode
    rate = np.exp(-env.dt / np.random.uniform(*timescale_limits))
    scale = np.random.uniform(*std_limits) * np.sqrt(1-rate*rate)

    # Start with zero actions
    actions = np.zeros((env.action_space.shape[0]))


    for step_idx in range(trajectory_length):

      # Add noise to actions
      actions = add_noise(actions, rate, scale)

      # Step
      env.step(actions)
      env.render()

      states[trajectory_idx, step_idx] = env.sim.data.qpos[env.independent_joints].copy()

  return states[:, ignore_first:]

if __name__=="__main__":

  env_name = 'UIB:mobl-arms-muscles-v0'
  train = False
  start_method = 'spawn' if 'Microsoft' in uname().release else 'forkserver'
#  generate_experience = True
#  experience_file = 'experience.npy'
  num_cpu = 48
  output_dir = os.path.join('output', env_name)
  checkpoint_dir = os.path.join(output_dir, 'checkpoint')
  log_dir = os.path.join(output_dir, 'log')

  # Leave for future kwargs
  env_kwargs = {}

#  if generate_experience:
#    experience = generate_random_trajectories(env, num_trajectories=1000, trajectory_length_seconds=10)
#    np.save(experience_file, experience)
#  else:
#    experience = np.load(experience_file)

  # Do the training
  if train:

    # Initialise parallel envs
    parallel_envs = make_vec_env(env_name, n_envs=num_cpu, seed=0, vec_env_cls=SubprocVecEnv, env_kwargs=env_kwargs,
                                 vec_env_kwargs={'start_method': start_method})

    # Policy parameters
    policy_kwargs = dict(activation_fn=torch.nn.LeakyReLU,
                         net_arch=[dict(pi=[256, 256], vf=[256, 256])],
                         log_std_init=0.0)
    lr = 3e-4

    # Initialise policy
    model = PPO('MlpPolicy', parallel_envs, verbose=1, policy_kwargs=policy_kwargs, tensorboard_log=log_dir)
                #learning_rate=linear_schedule(initial_value=lr, min_value=1e-7, threshold=0.8))

    # Initialise a callback for checkpoints
    save_freq = 1000000 // num_cpu
    checkpoint_callback = CheckpointCallback(save_freq=save_freq, save_path=checkpoint_dir, name_prefix='model')

    # Initialise a callback for linearly decaying standard deviation
    #std_callback = LinearStdDecayCallback(initial_log_value=policy_kwargs['log_std_init'],
    #                                      threshold=policy_kwargs['std_decay_threshold'],
    #                                      min_value=policy_kwargs['std_decay_min'])

    # Do the learning first with constant learning rate
    model.learn(total_timesteps=100_000_000, callback=[checkpoint_callback])

  else:

    # Load previous policy
    model = PPO.load(os.path.join(checkpoint_dir, 'model_75998784_steps'))


  # Initialise environment
  env = gym.make(env_name, **env_kwargs)

  # Visualise evaluations, perhaps save a video as well
  while not train:

    obs = env.reset()
#    env.render()
    done = False
    c = 0
    r = 0
    while not done:
      action, _states = model.predict(obs, deterministic=True)
      obs, rewards, done, info = env.step(action)
      env.model.tendon_rgba[:, 0] = 0.3 + env.sim.data.ctrl[2:] * 0.7
#      env.render()
      c += 1
      r += rewards
    print(c, r)