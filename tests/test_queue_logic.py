# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from unittest.mock import patch


class TestQueueLogic(TransactionCase):

    def setUp(self):
        super(TestQueueLogic, self).setUp()
        self.SmsMessage = self.env["sms_es.message"]
        self.QueueJob = self.env["sms_es.queue_job"]

    def test_01_deduplication_logic(self):
        """Prueba que los mensajes duplicados no se pongan en la cola."""
        # Crear un mensaje original ya enviado
        self.SmsMessage.create(
            {
                "name": "Original SMS",
                "sender": "TestSender",
                "receiver": "111222333",
                "text": "This is a test message.",
                "state": "delivered",
            }
        )

        # Intentar crear y encolar un mensaje idéntico
        duplicate_msg = self.SmsMessage.create(
            {
                "name": "Duplicate SMS",
                "sender": "TestSender",
                "receiver": "111222333",
                "text": "This is a test message.",
                "state": "draft",
            }
        )
        duplicate_msg.action_queue_sms()

        # Verificar que el mensaje duplicado se canceló y no se creó un trabajo
        self.assertEqual(duplicate_msg.state, "cancelled")
        job_count = self.QueueJob.search_count(
            [("message_id", "=", duplicate_msg.id)]
        )
        self.assertEqual(job_count, 0)

    @patch(
        "odoo.addons.sms_es_connector.\
           models.sms_es_client.SmsEsClient.send_sms"
    )
    def test_02_worker_backoff_on_failure(self, mock_send_sms):
        """Prueba que el worker programe un reintento si el envío falla."""
        mock_send_sms.return_value = {
            "status": "failed",
            "error": {"code": 503, "message": "Service Unavailable"},
        }

        msg = self.SmsMessage.create(
            {
                "name": "Test Backoff",
                "sender": "Odoo",
                "receiver": "444555666",
                "text": "Test retry logic.",
                "state": "draft",
            }
        )
        msg.action_queue_sms()

        job = self.QueueJob.search([("message_id", "=", msg.id)])
        self.assertTrue(job)

        # Simular la ejecución del worker
        self.QueueJob._process_sms_queue()

        job.invalidate_cache()
        # Vuelve a pendiente para el reintento
        self.assertEqual(job.state, "pending")
        self.assertEqual(job.retry_count, 1)
        self.assertTrue(job.next_try_datetime > job.create_date)
