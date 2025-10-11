# Copyright (C) Raffaele Salmaso <raffaele@salmaso.org>
# Copyright (C) Tom Forbes
# Copyright (C) Kenneth Reitz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDERS OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF
# THE POSSIBILITY OF SUCH DAMAGE.

import unittest

from django_service_urls import task


class CustomTaskBackendTestCase(unittest.TestCase):
    def test_custom_task_backend(self) -> None:
        result = task.parse("task://my.custom.TaskBackend?workers=4&timeout=300")
        self.assertEqual(result["BACKEND"], "my.custom.TaskBackend")
        self.assertEqual(result["OPTIONS"]["workers"], 4)
        self.assertEqual(result["OPTIONS"]["timeout"], 300)


class DjangoBuiltinTasksTestCase(unittest.TestCase):
    def test_dummy_backend(self) -> None:
        result = task.parse("dummy://?debug=true")
        self.assertEqual(result["BACKEND"], "django.tasks.backends.dummy.DummyBackend")
        self.assertEqual(result["OPTIONS"]["debug"], True)

    def test_immediate_backend(self) -> None:
        result = task.parse("immediate://?max_retries=3&timeout=60")
        self.assertEqual(result["BACKEND"], "django.tasks.backends.immediate.ImmediateBackend")
        self.assertEqual(result["OPTIONS"]["max_retries"], 3)
        self.assertEqual(result["OPTIONS"]["timeout"], 60)


class DjangoTasksBackendsTestCase(unittest.TestCase):
    def test_dummy_dt_backend(self) -> None:
        result = task.parse("dummy+dt://")
        self.assertEqual(result["BACKEND"], "django_tasks.backends.dummy.DummyBackend")

    def test_immediate_dt_backend(self) -> None:
        result = task.parse("immediate+dt://")
        self.assertEqual(result["BACKEND"], "django_tasks.backends.immediate.ImmediateBackend")

    def test_database_dt_backend(self) -> None:
        result = task.parse("database+dt://?db_table=tasks&retry.max_attempts=5&retry.delay=10")
        self.assertEqual(result["BACKEND"], "django_tasks.backends.database.DatabaseBackend")
        self.assertEqual(result["OPTIONS"]["db_table"], "tasks")
        self.assertEqual(result["OPTIONS"]["retry"]["max_attempts"], 5)
        self.assertEqual(result["OPTIONS"]["retry"]["delay"], 10)

    def test_rq_dt_backend(self) -> None:
        result = task.parse("rq+dt://?queue_name=high_priority&redis.host=localhost&redis.port=6379&redis.db=0")
        self.assertEqual(result["BACKEND"], "django_tasks.backends.rq.RQBackend")
        self.assertEqual(result["OPTIONS"]["queue_name"], "high_priority")
        self.assertEqual(result["OPTIONS"]["redis"]["host"], "localhost")
        self.assertEqual(result["OPTIONS"]["redis"]["port"], 6379)
        self.assertEqual(result["OPTIONS"]["redis"]["db"], 0)


if __name__ == "__main__":
    unittest.main()
