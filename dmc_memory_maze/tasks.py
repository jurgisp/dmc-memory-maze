import numpy as np
from dm_control import composer
from dm_control.locomotion.arenas import labmaze_textures

from dmc_memory_maze.maze import (FixedFloorTexture, FixedWallTexture,
                                  MazeWithTargetsArena, MemoryMazeTask,
                                  RollingBallWithFriction)
from dmc_memory_maze.wrappers import (DiscreteActionSetWrapper,
                                      ImageOnlyObservationWrapper,
                                      RemapObservationWrapper,
                                      TargetColorAsBorderWrapper,
                                      TargetPosWrapper)

# Slow control (4Hz), so that agent without HRL has a chance.
# Native control would be 40Hz, so this corresponds roughly to action_repeat=10.
DEFAULT_CONTROL_FREQ = 4

def memory_maze_9x9(**kwargs):
    """
    Maze based on DMLab30-explore_goal_locations_small
    {
        mazeHeight = 11,  # with outer walls
        mazeWidth = 11,
        roomCount = 4,
        roomMaxSize = 5,
        roomMinSize = 3,
    }
    """
    return _memory_maze(9, 3, 250, **kwargs)

def memory_maze_11x11(**kwargs):
    return _memory_maze(11, 4, 500, **kwargs)

def memory_maze_13x13(**kwargs):
    return _memory_maze(13, 5, 750, **kwargs)

def memory_maze_15x15(**kwargs):
    """
    Maze based on DMLab30-explore_goal_locations_large
    {
        mazeHeight = 17,  # with outer walls
        mazeWidth = 17,
        roomCount = 9,
        roomMaxSize = 3,
        roomMaxSize = 3,
    }
    """
    return _memory_maze(15, 6, 1000, max_rooms=9, room_max_size=3, **kwargs)

def _memory_maze(
    maze_size,  # measured without exterior walls
    n_targets,
    time_limit,
    max_rooms=6,
    room_min_size=3,
    room_max_size=5,
    control_freq=DEFAULT_CONTROL_FREQ,
    discrete_actions=True,
    target_color_in_image=True,
    image_only_obs=False,
    top_camera=False,
    good_visibility=False,
    camera_resolution=64,
    random_state=None,
):
    walker = RollingBallWithFriction(camera_height=0.3, add_ears=top_camera)
    arena = MazeWithTargetsArena(
        x_cells=maze_size + 2,  # inner size => outer size
        y_cells=maze_size + 2,
        xy_scale=2.0,
        z_height=1.5 if not good_visibility else 0.4,
        max_rooms=max_rooms,
        room_min_size=room_min_size,
        room_max_size=room_max_size,
        spawns_per_room=1,
        targets_per_room=1,
        floor_textures=FixedFloorTexture('style_01', ['blue', 'blue_bright']),
        wall_textures=dict({
            '*': FixedWallTexture('style_01', 'yellow'),  # default wall
        }, **{str(i): labmaze_textures.WallTextures('style_01') for i in range(10)}  # variations
        ),
        skybox_texture=None,
    )

    task = MemoryMazeTask(
        walker=walker,
        maze_arena=arena,
        n_targets=n_targets,
        target_radius=0.6,
        target_height_above_ground=0.5 if good_visibility else -0.6,
        enable_global_task_observables=True,
        control_timestep=1.0 / control_freq,
        camera_resolution=camera_resolution,
    )

    if top_camera:
        task.observables['top_camera'].enabled = True

    env = composer.Environment(
        time_limit=time_limit - 1e-3,  # subtract epsilon to make sure ep_length=time_limit*fps
        task=task,
        random_state=random_state,
        strip_singleton_obs_buffer_dim=True)

    env = TargetPosWrapper(env)

    env = RemapObservationWrapper(env, {
        'image': 'walker/egocentric_camera' if not top_camera else 'top_camera',
        'target_color': 'target_color',
    })

    if target_color_in_image:
        env = TargetColorAsBorderWrapper(env)
    if image_only_obs:
        assert target_color_in_image, 'Image-only observation only makes sense with target_color_in_image'
        env = ImageOnlyObservationWrapper(env)

    if discrete_actions:
        env = DiscreteActionSetWrapper(env, [
            np.array([0.0, 0.0]),  # noop
            np.array([-1.0, 0.0]),  # forward
            np.array([0.0, -1.0]),  # left
            np.array([0.0, +1.0]),  # right
            np.array([-1.0, -1.0]),  # forward + left
            np.array([-1.0, +1.0]),  # forward + right
        ])

    return env
