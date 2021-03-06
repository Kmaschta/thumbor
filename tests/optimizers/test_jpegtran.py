#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/thumbor/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com thumbor@googlegroups.com

from thumbor.config import Config
from thumbor.context import Context, RequestParameters
from thumbor.optimizers.jpegtran import Optimizer

from unittest import TestCase

import mock


class JpegtranOptimizerTest(TestCase):
    def setUp(self):
        self.patcher = mock.patch('thumbor.optimizers.jpegtran.Popen')
        self.mock_popen = self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def get_optimizer(self, filters=None, progressive=False):
        conf = Config()
        conf.STATSD_HOST = ''
        conf.JPEGTRAN_PATH = '/somewhere/jpegtran'
        conf.PROGRESSIVE_JPEG = progressive
        req = RequestParameters(filters=filters)
        ctx = Context(config=conf)
        ctx.request = req
        optimizer = Optimizer(ctx)

        return optimizer

    def test_should_run_for_jpeg(self):
        optimizer = self.get_optimizer()
        self.assertTrue(optimizer.should_run('.jpg', ''))
        self.assertTrue(optimizer.should_run('.jpeg', ''))

    def test_should_not_run_for_not_jpeg(self):
        optimizer = self.get_optimizer()

        self.assertFalse(optimizer.should_run('.png', ''))
        self.assertFalse(optimizer.should_run('.webp', ''))
        self.assertFalse(optimizer.should_run('.gif', ''))

    def test_should_optimize(self):
        input = 'input buffer'
        output = 'output buffer'
        self.mock_popen.return_value.returncode = 0
        self.mock_popen.return_value.communicate.return_value = (output, "Error")

        optimizer = self.get_optimizer()
        return_buffer = optimizer.run_optimizer('.jpg', input)

        self.mock_popen.return_value.communicate.assert_called_with(input)
        self.assertEqual(output, return_buffer)

    def test_should_return_old_buffer_for_invalid_extension(self):
        optimizer = self.get_optimizer()
        buffer = 'garbage'

        return_buffer = optimizer.run_optimizer('.png', buffer)

        self.assertEqual(return_buffer, buffer)

    def test_should_return_old_buffer_for_invalid_image(self):
        optimizer = self.get_optimizer()
        buffer = 'garbage'

        self.mock_popen.return_value.returncode = 1
        self.mock_popen.return_value.communicate.return_value = ('Output', 'Error')

        return_buffer = optimizer.run_optimizer('.jpg', buffer)

        self.assertEqual(return_buffer, buffer)

    def test_should_preserve_comments_if_strip_icc_filter_set(self):
        self.mock_popen.return_value.returncode = 0
        self.mock_popen.return_value.communicate.return_value = ('Output', 'Error')

        optimizer = self.get_optimizer(filters=['strip_icc'])
        optimizer.run_optimizer('.jpg', '')

        command = self.mock_popen.call_args[0][0]

        self.assertIn('-copy', command)
        self.assertIn('comments', command)
        self.assertNotIn('all', command)

        optimizer = self.get_optimizer()
        optimizer.run_optimizer('.jpg', '')

        command = self.mock_popen.call_args[0][0]

        self.assertIn('-copy', command)
        self.assertIn('all', command)
        self.assertNotIn('comments', command)

    def test_should_make_progressive_when_configured(self):
        self.mock_popen.return_value.returncode = 0
        self.mock_popen.return_value.communicate.return_value = ('Output', 'Error')

        optimizer = self.get_optimizer(progressive=False)
        optimizer.run_optimizer('.jpg', '')

        args, _ = self.mock_popen.call_args
        command = args[0]

        self.assertNotIn('-progressive', command)

        optimizer = self.get_optimizer(progressive=True)
        optimizer.run_optimizer('.jpg', '')

        args, _ = self.mock_popen.call_args
        command = args[0]

        self.assertIn('-progressive', command)

    @mock.patch('thumbor.optimizers.jpegtran.logger.warn')
    def test_should_log_warning_when_failed(self, warn_logger):
        optimizer = self.get_optimizer()

        self.mock_popen.return_value.returncode = 1
        self.mock_popen.return_value.communicate.return_value = ('Output', 'Error')

        optimizer.run_optimizer('.jpg', 'garbage')

        warn_logger.assert_called_once()
