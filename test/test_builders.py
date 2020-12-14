# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import getpass
from pathlib import Path
from typing import NamedTuple
from unittest.mock import Mock

import pytest

from ros_cross_compile.builders import EmulatedDockerBuildStage
from ros_cross_compile.data_collector import DataCollector
from ros_cross_compile.dependencies import rosdep_install_script
from ros_cross_compile.docker_client import DockerClient
from ros_cross_compile.pipeline_stages import PipelineStageOptions
from ros_cross_compile.platform import Platform
from ros_cross_compile.sysroot_creator import CreateSysrootStage
from ros_cross_compile.sysroot_creator import prepare_docker_build_environment

from .utilities import default_pipeline_options
from .utilities import uses_docker


def _touch_anywhere(path: Path):
    """Make the parent directories of a given path and then touch the file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()


def test_emulated_docker_build():
    # Very simple smoke test to validate that all internal syntax is correct
    mock_docker_client = Mock()
    mock_data_collector = Mock()
    platform = Platform('aarch64', 'ubuntu', 'eloquent')

    stage = EmulatedDockerBuildStage()
    stage(
        platform,
        mock_docker_client,
        Path('dummy_path'),
        default_pipeline_options(),
        mock_data_collector)

    assert mock_docker_client.run_container.call_count == 1


def test_docker_build_stage_creation():
    temp_stage = EmulatedDockerBuildStage()
    assert temp_stage


BuildableEnv = NamedTuple('BuildableEnv', [
    ('platform', Platform),
    ('docker', DockerClient),
    ('ros_workspace', Path),
    ('options', PipelineStageOptions),
    ('data_collector', DataCollector)
])


@pytest.fixture
def buildable_env(tmpdir):
    """Set up a temporary directory with everything needed to run the EmulatedDockerBuildStage."""
    platform = Platform('aarch64', 'ubuntu', 'foxy')
    ros_workspace = Path(str(tmpdir)) / 'ros_ws'
    _touch_anywhere(ros_workspace / rosdep_install_script(platform))
    build_context = prepare_docker_build_environment(platform, ros_workspace)
    docker = DockerClient(disable_cache=False, default_docker_dir=build_context)
    options = default_pipeline_options()
    data_collector = DataCollector()

    CreateSysrootStage()(
        platform, docker, ros_workspace, options, data_collector)

    return BuildableEnv(platform, docker, ros_workspace, options, data_collector)


@uses_docker
def test_build_ownership_on_success(buildable_env):
    EmulatedDockerBuildStage()(
        buildable_env.platform,
        buildable_env.docker,
        buildable_env.ros_workspace,
        buildable_env.options,
        buildable_env.data_collector)

    # make sure all files are owned by the current user
    user = getpass.getuser()
    for p in buildable_env.ros_workspace.rglob('*'):
        assert user == p.owner()
