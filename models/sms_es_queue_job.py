# -*- coding: utf-8 -*-
import logging
from datetime import datetime, timedelta

from odoo import models, fields, api
from .sms_es_client import SmsEsClient

_logger = logging.getLogger(__name__)


class SmsEsQueueJob(models.Model):
    _name = "sms_es.queue_job"
    _description = "Cola de Trabajos de SMS"

    name = fields.Char(
        string="Nombre del Trabajo", required=True, readonly=True
    )
    message_id = fields.Many2one(
        "sms_es.message",
        string="Mensaje SMS",
        required=True,
        ondelete="cascade",
        readonly=True,
    )
    state = fields.Selection(
        [
            ("pending", "Pendiente"),
            ("in_progress", "En Progreso"),
            ("success", "Éxito"),
            ("failed", "Fallido"),
            ("cancelled", "Cancelado"),
        ],
        string="Estado",
        default="pending",
        required=True,
        index=True,
    )
    retry_count = fields.Integer(
        string="Contador de Reintentos", default=0, readonly=True
    )
    max_retries = fields.Integer(string="Máximos Reintentos", default=5)
    next_try_datetime = fields.Datetime(
        string="Próximo Intento", default=fields.Datetime.now, index=True
    )
    delay_seconds = fields.Integer(string="Retardo (segundos)", default=60)
    error_message = fields.Text(string="Mensaje de Error", readonly=True)
    priority = fields.Integer(string="Prioridad", default=10)

    @api.model
    def _process_sms_queue(self, limit=100):
        """
        Método principal del cron worker.
        Procesa trabajos pendientes cuyo momento de reintento ha llegado.
        """
        # Dominio para buscar trabajos listos para ser procesados
        domain = [
            ("state", "=", "pending"),
            ("next_try_datetime", "<=", fields.Datetime.now()),
        ]
        jobs_to_process = self.search(
            domain, order="priority desc, create_date asc", limit=limit
        )

        _logger.info(
            "Worker de la cola de SMS iniciado. %d trabajos para procesar.",
            len(jobs_to_process),
        )

        if not jobs_to_process:
            return

        # Instanciar el cliente una sola vez para mejorar el rendimiento
        try:
            api_client = SmsEsClient(self.env)
        except Exception as e:
            _logger.error(
                "No se pudo inicializar el cliente de la API de \
                    SMS.es: %s. Abortando el worker.",
                e,
            )
            return

        for job in jobs_to_process:
            try:
                job.write({"state": "in_progress"})
                # Confirmar el cambio de estado para 
                # evitar que otro worker lo tome
                self.env.cr.commit()  

                message = job.message_id
                message_data = {
                    "receiver": message.receiver,
                    "sender": message.sender,
                    "text": message.text,
                    "odoo_message_id": message.id,
                }

                result = api_client.send_sms(message_data)

                if result.get("status") == "success":
                    # --- Manejo de éxito ---
                    message.write(
                        {
                            "state": "api_sent",
                            "msg_id": result["data"].get("msgId"),
                            "num_parts": result["data"].get("numParts"),
                        }
                    )
                    job.write({"state": "success", "error_message": False})
                else:
                    # --- Manejo de fallo ---
                    self._handle_send_failure(job, result.get("error", {}))

            except Exception as e:
                _logger.error(
                    "Error inesperado procesando el trabajo de SMS %d: %s", 
                    job.id, e
                )
                self.env.cr.rollback()
                self._handle_send_failure(job, {"code": -1, "message": str(e)})

            self.env.cr.commit()

    def _handle_send_failure(self, job, error_info):
        """
        Gestiona un fallo de envío, decide si reintentar o marcar como fallido.
        """
        error_message = (
            f"Code: {error_info.get('code')} \
                - Message: {error_info.get('message')}"
        )

        if job.retry_count < job.max_retries:
            # --- Programar reintento ---
            new_retry_count = job.retry_count + 1
            delay = job.delay_seconds * new_retry_count  # Backoff lineal 
            next_try = datetime.now() + timedelta(seconds=delay)

            job.write(
                {
                    "state": "pending",  # pendiente para el próximo intento
                    "retry_count": new_retry_count,
                    "next_try_datetime": next_try,
                    "error_message": error_message,
                }
            )
            _logger.warning(
                "Fallo en el envío del trabajo %d. \
                    Reintento %d/%d programado para %s.",
                job.id,
                new_retry_count,
                job.max_retries,
                next_try,
            )
        else:
            # --- Marcar como fallido permanentemente ---
            job.message_id.write({"state": "api_failed"})
            job.write(
                {
                    "state": "failed",
                    "error_message": f"Fallo final después de \
                        {job.max_retries} reintentos. Último \
                            error: {error_message}",
                }
            )
            _logger.error("El trabajo de SMS %d ha fallado permanentemente.", 
                          job.id)
