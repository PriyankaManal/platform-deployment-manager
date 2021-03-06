"""
Name:       test_package_registrar.py
Purpose:    Unit tests for the hbase package registrar
            Run with main(), the easiest way is "nosetests test_*.py"
Author:     PNDA team

Created:    21/03/2016

Copyright (c) 2016 Cisco and/or its affiliates.

This software is licensed to you under the terms of the Apache License, Version 2.0 (the "License").
You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0

The code, technical concepts, and all information contained herein, are the property of Cisco Technology, Inc.
and/or its affiliated entities, under various laws including copyright, international treaties, patent,
and/or contract. Any use of the material herein must be in accordance with the terms of the License.
All rights not expressly granted by the License are reserved.

Unless required by applicable law or agreed to separately in writing, software distributed under the
License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied.
"""

import unittest
import json
import happybase # pylint: disable=unused-import
from mock import patch, mock_open, Mock
from Hbase_thrift import AlreadyExists
from package_registrar import HbasePackageRegistrar

from lifecycle_states import PackageDeploymentState


class GenerateRecord(unittest.TestCase):

    def test_generate_record(self):
        store = HbasePackageRegistrar(None, None, None, None, None)
        metadata = {
            "component_types": {
                "sparkStreaming": {
                    "componentC": {
                        "component_detail": {
                            "properties.json": {
                                "property1": "1",
                                "property2": "two"}},
                        "component_path": "test_package-1.0.2/sparkStreaming/componentC",
                        "component_name": "componentC"}}},
            "package_name": "test_package-1.0.2"}

        package_data_path = '/user/pnda/application_packages/test_package-1.0.2'

        expected_record = metadata["package_name"], {
            'cf:name': 'test_package',
            'cf:version': '1.0.2',
            'cf:metadata': json.dumps(metadata),
            'cf:package_data': package_data_path
        }

        self.assertEqual(
            store.generate_record(metadata),
            expected_record)

    @patch('happybase.Connection')
    @patch('package_registrar.PackageParser')
    @patch('deployer_utils.HDFS')
    # pylint: disable=unused-argument
    # pylint: disable=protected-access
    def test_download_package(self, hdfs_mock, parser_mock, hbase_mock):
        parser_mock.return_value.get_package_metadata.return_value = {"package_name": "a-1"}

        registrar = HbasePackageRegistrar('1.2.3.4', None, None, None, None)
        registrar._hdfs_client = Mock()
        with patch("__builtin__.open", mock_open(read_data="1234")):
            registrar.set_package('name', 'abcd')

        hbase_mock.return_value.table.return_value.put.assert_called_once_with(
            'a-1',
            {'cf:metadata': '{"package_name": "a-1"}', 'cf:package_data': '/user/pnda/application_packages/a-1', 'cf:name': 'a', 'cf:version': '1'})

    @patch('happybase.Connection')
    def test_set_package_deploy_status(self, hbase_mock):
        registrar = HbasePackageRegistrar('1.2.3.4', None, None, None, None)
        registrar.set_package_deploy_status('name', PackageDeploymentState.DEPLOYED)

        hbase_mock.return_value.table.return_value.put.assert_called_once_with('name', {'cf:deploy_status': '"%s"' % PackageDeploymentState.DEPLOYED})

    @patch('happybase.Connection')
    # pylint: disable=protected-access
    def test_delete_package(self, hbase_mock):
        registrar = HbasePackageRegistrar('1.2.3.4', None, None, None, None)
        registrar._hdfs_client = Mock()
        registrar.delete_package('name')
        hbase_mock.return_value.table.return_value.delete.assert_called_once_with('name')

    @patch('happybase.Connection')
    # pylint: disable=protected-access
    def test_table_exists(self, hbase_mock):
        def throwerr(arg1, arg2):
            raise AlreadyExists("%s%s" % (arg1, arg2))

        hbase_mock.return_value.create_table.side_effect = throwerr

        registrar = HbasePackageRegistrar('1.2.3.4', None, None, None, None)
        registrar._hdfs_client = Mock()
        registrar.delete_package('name')
        hbase_mock.return_value.table.return_value.delete.assert_called_once_with('name')

    @patch('happybase.Connection')
    # pylint: disable=unused-argument
    # pylint: disable=protected-access
    def test_get_package_data(self, hbase_mock):
        hbase_mock.return_value.table.return_value.row.return_value = {'cf:package_data': 'abcd'}

        registrar = HbasePackageRegistrar('1.2.3.4', None, None, None, 'path')
        registrar._hdfs_client = Mock()

        with patch("__builtin__.open", mock_open(read_data="1234")):
            result = registrar.get_package_data('name')

        self.assertEqual(result, 'path/name')
        hbase_mock.return_value.table.return_value.row.return_value = {}

        result = registrar.get_package_data('name')
        self.assertEqual(result, None)

    @patch('happybase.Connection')
    def test_get_package_metadata(self, hbase_mock):
        hbase_mock.return_value.table.return_value.row.return_value = {'cf:metadata': '{"some": "thing"}', 'cf:name': 'name', 'cf:version': '1.0.0'}

        registrar = HbasePackageRegistrar('1.2.3.4', None, None, None, None)
        result = registrar.get_package_metadata('name')

        self.assertEqual(result, {'version': '1.0.0', 'name': 'name', 'metadata': {u'some': u'thing'}})
        hbase_mock.return_value.table.return_value.row.return_value = {}

        result = registrar.get_package_metadata('name')
        self.assertEqual(result, None)

    @patch('happybase.Connection')
    def test_package_exists(self, hbase_mock):
        hbase_mock.return_value.table.return_value.row.return_value = {'cf:metadata': '{"some": "thing"}', 'cf:name': 'name', 'cf:version': '1.0.0'}

        registrar = HbasePackageRegistrar('1.2.3.4', None, None, None, None)
        result = registrar.package_exists('name')
        self.assertEqual(result, True)

        hbase_mock.return_value.table.return_value.row.return_value = {}

        result = registrar.package_exists('name')
        self.assertEqual(result, False)

    @patch('happybase.Connection')
    def test_get_package_deploy_status(self, hbase_mock):
        hbase_mock.return_value.table.return_value.row.return_value = {'cf:deploy_status': '"%s"' % PackageDeploymentState.DEPLOYED}

        registrar = HbasePackageRegistrar('1.2.3.4', None, None, None, None)
        result = registrar.get_package_deploy_status('name')
        self.assertEqual(result, PackageDeploymentState.DEPLOYED)

        hbase_mock.return_value.table.return_value.row.return_value = {}

        result = registrar.get_package_deploy_status('name')
        self.assertEqual(result, None)

    @patch('happybase.Connection')
    def test_list_packages(self, hbase_mock):
        hbase_mock.return_value.table.return_value.scan.return_value = [('name1', None), ('name2', None)]

        registrar = HbasePackageRegistrar('1.2.3.4', None, None, None, None)
        result = registrar.list_packages()
        self.assertEqual(result, ['name1', 'name2'])
