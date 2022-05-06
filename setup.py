from setuptools import setup

setup(name='uitb',
      version='0.1.1',
      author="Aleksi Ikkala",
      author_email="aleksi.ikkala@aalto.fi",
      packages=["uitb"],
      install_requires=['gym', 'mujoco_py', 'stable-baselines3', 'tensorboard', 'torch']
)