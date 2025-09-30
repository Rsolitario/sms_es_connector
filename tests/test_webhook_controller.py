# -*- coding: utf-8 -*-
import json
from odoo.tests.common import HttpCase, tagged

@tagged('post_install', '-at_install')
class TestWebhookController(HttpCase):

    def setUp(self):
        super(TestWebhookController, self).setUp()
        self.env = self.env(user=self.env.ref('base.user_root'))
        self.SmsMessage = self.env['sms_es.message']
        # Configurar un token
        self.token = 'SECRET_TEST_TOKEN'
        self.env['ir.config_parameter'].sudo().set_param('sms_es_connector.webhook_token', self.token)
        self.webhook_url = f'/sms_es_connector/webhook/dlr?token={self.token}'

    def test_01_webhook_invalid_token(self):
        """Prueba que el webhook rechace peticiones con un token inválido."""
        response = self.url_open(
            url='/sms_es_connector/webhook/dlr?token=WRONG_TOKEN',
            data=json.dumps({}),
            headers={'Content-Type': 'application/json'}
        )
        self.assertEqual(response.status_code, 401)

    def test_02_webhook_successful_dlr_custom_id(self):
        """Prueba el procesamiento exitoso de un DLR usando odoo_message_id."""
        msg = self.SmsMessage.create({
            'name': 'Test DLR', 'sender': 'Odoo', 'receiver': '777888999',
            'text': 'Test DLR processing.', 'state': 'api_sent', 'msg_id': 'api-uuid-should-be-ignored'
        })

        dlr_payload = {
            'event': 'DELIVERED', 'msgId': 'some-api-id',
            'custom': {'odoo_message_id': msg.id}
        }
        
        response = self.url_open(
            url=self.webhook_url,
            data=json.dumps(dlr_payload),
            headers={'Content-Type': 'application/json'}
        )

        self.assertEqual(response.status_code, 200)
        msg.invalidate_cache()
        self.assertEqual(msg.state, 'delivered')
        self.assertEqual(len(msg.dlr_event_ids), 1)
        self.assertEqual(msg.dlr_event_ids[0].event, 'DELIVERED')

    def test_03_webhook_successful_dlr_fallback_msgid(self):
        """Prueba el procesamiento exitoso de un DLR usando el msgId como fallback."""
        msg_uuid = 'api-uuid-for-fallback-test'
        msg = self.SmsMessage.create({
            'name': 'Test DLR Fallback', 'sender': 'Odoo', 'receiver': '123123123',
            'text': 'Test DLR processing.', 'state': 'api_sent', 'msg_id': msg_uuid
        })

        dlr_payload = {'event': 'UNDELIVERED', 'msgId': msg_uuid}
        
        response = self.url_open(
            url=self.webhook_url,
            data=json.dumps(dlr_payload),
            headers={'Content-Type': 'application/json'}
        )

        self.assertEqual(response.status_code, 200)
        msg.invalidate_cache()
        self.assertEqual(msg.state, 'undelivered')