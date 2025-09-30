# -*- coding: utf-8 -*-
import requests
import time
from unittest.mock import patch, MagicMock

from odoo.tests.common import BaseCase
from odoo.addons.sms_es_connector.models.sms_es_client import SmsEsClient, RC_THROTTLING_ERROR

class TestSmsEsApiClient(BaseCase):

    def setUp(self):
        super(TestSmsEsApiClient, self).setUp()
        # Simular configuración en Odoo
        self.env['ir.config_parameter'].set_param('sms_es_connector.api_url', 'http://fakeapi.com/sendsms')
        self.env['ir.config_parameter'].set_param('sms_es_connector.api_username', 'user')
        self.env['ir.config_parameter'].set_param('sms_es_connector.api_password', 'pass')
        self.client = SmsEsClient(self.env)
        self.message_data = {'receiver': '123456789', 'sender': 'Odoo', 'text': 'Test', 'odoo_message_id': 1}

    @patch('requests.post')
    def test_01_send_sms_success_202(self, mock_post):
        """Prueba de envío exitoso con respuesta HTTP 202."""
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_response.json.return_value = {'msgId': 'fake-uuid-123', 'numParts': 1}
        mock_post.return_value = mock_response

        result = self.client.send_sms(self.message_data)

        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['data']['msgId'], 'fake-uuid-123')
        mock_post.assert_called_once()

    @patch('requests.post')
    def test_02_send_sms_rejected_420(self, mock_post):
        """Prueba de rechazo de la API con respuesta HTTP 420."""
        mock_response = MagicMock()
        mock_response.status_code = 420
        mock_response.json.return_value = {'error': {'code': 101, 'message': 'Authentication failed'}}
        mock_post.return_value = mock_response

        result = self.client.send_sms(self.message_data)

        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['error']['code'], 101)
        mock_post.assert_called_once()

    @patch('time.sleep', return_value=None)
    @patch('requests.post')
    def test_03_send_sms_throttling_retry_105(self, mock_post, mock_sleep):
        """Prueba de reintento tras un error de throttling (código 105)."""
        success_response = MagicMock(status_code=202, json=lambda: {'msgId': 'uuid', 'numParts': 1})
        throttling_response = MagicMock(status_code=420, json=lambda: {'error': {'code': RC_THROTTLING_ERROR, 'message': 'Throttling'}})
        mock_post.side_effect = [throttling_response, success_response]

        result = self.client.send_sms(self.message_data)

        self.assertEqual(result['status'], 'success')
        self.assertEqual(mock_post.call_count, 2)
        mock_sleep.assert_called_once_with(1) # Espera de 1 segundo

    @patch('time.sleep', return_value=None)
    @patch('requests.post')
    def test_04_send_sms_server_error_retry_500(self, mock_post, mock_sleep):
        """Prueba de reintento tras un error de servidor HTTP 500."""
        success_response = MagicMock(status_code=202, json=lambda: {'msgId': 'uuid', 'numParts': 1})
        server_error_response = MagicMock(status_code=500, text="Internal Server Error")
        mock_post.side_effect = [server_error_response, success_response]

        result = self.client.send_sms(self.message_data)

        self.assertEqual(result['status'], 'success')
        self.assertEqual(mock_post.call_count, 2)
        mock_sleep.assert_called_once_with(60) # Espera de 1 minuto