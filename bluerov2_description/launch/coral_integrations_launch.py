from simple_launch import SimpleLauncher
from launch.actions import TimerAction, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python.packages import get_package_share_directory
import os

def generate_launch_description():
    sl = SimpleLauncher()
    
    sl.declare_arg('gui', default_value=True)
    sl.declare_arg('depth', default_value=-5.)
    
    # 1. Mundo e Robô (subem primeiro usando o SimpleLauncher normal)
    sl.include('bluerov2_description', 'coral_world_textura_launch.py',
               launch_arguments={
                   'gui': sl.arg('gui'),
                   'spawn': True,
                   'depth': sl.arg('depth')
               })
    
    # 2. Caminho para o launch do PID
    pid_launch_path = os.path.join(
        get_package_share_directory('bluerov2_control'),
        'launch',
        'cascaded_pids_launch.py'
    )
    
    # 3. PID com atraso real de 3 segundos usando nativo do ROS 2
    delayed_pid = TimerAction(
        period=3.0,
        actions=[
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(pid_launch_path),
                launch_arguments={
                    'sliders': 'false',
                    'rviz': 'false',
                    'world_frame': 'world',
                    'use_sim_time': 'true'
                }.items()
            )
        ]
    )
    
    sl.add_action(delayed_pid)

    return sl.launch_description()
