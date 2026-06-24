#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import unittest
from unittest import mock

import yolo_detect_gateway_client as gateway_client


class YoloDetectGatewayClientApiTest(unittest.TestCase):
    def test_detect_once_returns_success_payload(self) -> None:
        payload = {"status": "success", "request_id": "demo", "offset": {"direction": "偏左"}}

        with mock.patch.object(gateway_client, "GatewayYoloDetectClient", autospec=True) as client_cls:
            client = client_cls.return_value
            client.run.return_value = 0
            client.result = payload
            client.request_id = "demo"

            result = gateway_client.detect_once(verbose=False, output_json="")

        self.assertEqual(result, payload)
        client_cls.assert_called_once()
        self.assertFalse(client_cls.call_args.args[0].verbose)
        self.assertEqual(client_cls.call_args.args[0].output_json, "")

    def test_detect_once_raises_on_error_result(self) -> None:
        with mock.patch.object(gateway_client, "GatewayYoloDetectClient", autospec=True) as client_cls:
            client = client_cls.return_value
            client.run.return_value = 1
            client.result = {"status": "error", "error": "bad image"}
            client.request_id = "demo"

            with self.assertRaisesRegex(RuntimeError, "bad image"):
                gateway_client.detect_once(verbose=False)

    def test_detect_once_can_return_error_without_raise(self) -> None:
        payload = {"status": "error", "error": "bad image"}
        with mock.patch.object(gateway_client, "GatewayYoloDetectClient", autospec=True) as client_cls:
            client = client_cls.return_value
            client.run.return_value = 1
            client.result = payload
            client.request_id = "demo"

            result = gateway_client.detect_once(verbose=False, raise_on_error=False)

        self.assertEqual(result, payload)


if __name__ == "__main__":
    unittest.main()
