"""robot_state_publisher + RViz + Qt Creator 로 만든 IK 조종기(mainwindow.ui)를 한 번에 켠다.

joint_state_publisher_gui 는 켜지 않는다 (IK 컨트롤러가 /joint_states 를 보낸다).
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    desc_share = FindPackageShare('robot_description')
    xacro_file = PathJoinSubstitution([desc_share, 'urdf', 'eclipse.xacro'])
    rviz_file = PathJoinSubstitution([desc_share, 'config', 'eclipse.rviz'])

    base_link = LaunchConfiguration('base_link')
    tip_link = LaunchConfiguration('tip_link')

    return LaunchDescription([
        DeclareLaunchArgument('base_link', default_value='mani_base_link'),
        DeclareLaunchArgument('tip_link', default_value='gripper_base_link'),
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            parameters=[{'robot_description': ParameterValue(Command(['xacro ', xacro_file]), value_type=str)}],
        ),
        Node(
            package='rviz2',
            executable='rviz2',
            arguments=['-d', rviz_file],
        ),
        Node(
            package='ik_gui',
            executable='mani_ui',
            parameters=[{'base_link': base_link, 'tip_link': tip_link}],
            output='screen',
        ),
    ])
