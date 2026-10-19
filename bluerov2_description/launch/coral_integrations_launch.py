from simple_launch import SimpleLauncher

def generate_launch_description():
    sl = SimpleLauncher()
    
    sl.declare_arg('gui', default_value=True)
    sl.declare_arg('depth', default_value=-5.)
    
    # 1. Mundo e Robô
    sl.include('bluerov2_description', 'coral_world_textura_launch.py',
               launch_arguments={
                   'gui': sl.arg('gui'),
                   'spawn': True,
                   'depth': sl.arg('depth')
               })
    
    # 2. PID alinhado com o frame correto da simulação
    sl.include('bluerov2_control', 'cascaded_pids_launch.py',
               launch_arguments={
                   'sliders': False,
                   'rviz': False,
                   'world_frame': 'world'
               })

    return sl.launch_description()