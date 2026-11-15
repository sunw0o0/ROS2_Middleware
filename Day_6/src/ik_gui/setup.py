from glob import glob
from setuptools import setup

package_name = 'ik_gui'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
        ('share/' + package_name + '/ui', glob('ui/*.ui')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='sunwoo',
    maintainer_email='user@example.com',
    description='Qt IK controller for RViz',
    license='MIT',
    entry_points={
        'console_scripts': [
            'mani_ui = ik_gui.mani_ui_node:main',
        ],
    },
)
