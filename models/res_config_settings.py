# -*- coding: utf-8 -*-
from odoo import models, fields, api
import uuid


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # --- API Credentials ---
    sms_es_api_username = fields.Char(
        string="API Username",
        config_parameter="sms_es_connector.api_username",
        help="Nombre de usuario para la autenticación en la API de SMS.es.",
    )
    sms_es_api_password = fields.Char(
        string="API Password",
        # password=True,
        config_parameter="sms_es_connector.api_password",
        help="Contraseña para la autenticación en la API.",
    )

    # --- Default Sending Options ---
    sms_es_default_sender = fields.Char(
        string="Remitente por Defecto",
        config_parameter="sms_es_connector.default_sender",
        help="Remitente que se usará si no se especifica uno.",
    )
    sms_es_api_url = fields.Char(
        string="URL del Endpoint de Envío",
        config_parameter="sms_es_connector.api_url",
        default="https://sms.example.org/bulk/sendsms",
        help="URL completa del endpoint de la API para el envío de SMS.",
    )
    sms_es_dlr_mask = fields.Integer(
        string="Máscara DLR",
        config_parameter="sms_es_connector.dlr_mask",
        default=19,
        help="Valor numérico para solicitar informes de entrega (DLR). "
        "Recomendado: 19 (Suma de 1=DELIVERED, 2=UNDELIVERED, 16=REJECTED).",
    )
    sms_es_dlr_url = fields.Char(
        string="URL del Webhook DLR",
        readonly=True,
        compute="_compute_dlr_url",
        help="URL que debe configurar en su proveedor \
            de SMS para recibir los DLRs.",
    )
    sms_es_dcs = fields.Selection(
        [
            ("gsm", "GSM (caracteres estándar)"),
            ("ucs", "UCS-2 (caracteres especiales/Unicode)"),
        ],
        string="Codificación de Datos (DCS)",
        config_parameter="sms_es_connector.dcs",
        default="gsm",
        required=True,
    )

    # --- Advanced Options ---
    sms_es_use_flash = fields.Boolean(
        string="Activar Mensajes Flash",
        config_parameter="sms_es_connector.use_flash",
        help="Si se activa, los mensajes se enviarán como \
            'flash' (no se guardan en el dispositivo).",
    )
    sms_es_use_validate_period = fields.Boolean(
        string="Activar Periodo de Validez",
        config_parameter="sms_es_connector.use_validate_period",
        help="Permite definir un tiempo máximo \
            de validez para el mensaje en la red.",
    )
    sms_es_validate_period_minutes = fields.Integer(
        string="Periodo de Validez (minutos)",
        config_parameter="sms_es_connector.validate_period_minutes",
        default=1440,  # 24 horas
        help="Tiempo en minutos durante el cual \
            el SMS será válido para su entrega.",
    )

    # --- Worker Configuration ---
    sms_es_cron_frequency_minutes = fields.Integer(
        string="Frecuencia del Worker (minutos)",
        default=1,
        help="Intervalo en minutos con el que el \
            cron procesará la cola de envíos.",
    )

    # --- Webhook Security ---
    sms_es_webhook_token = fields.Char(
        string="Webhook Secret Token",
        config_parameter="sms_es_connector.webhook_token",
        default=lambda self: uuid.uuid4().hex,  # Generar un token por defecto
        help="Token secreto para añadir a la URL \
            del webhook como medida de seguridad.",
    )

    sms_es_webhook_hmac_secret = fields.Char(
        string="Webhook HMAC Secret",
        config_parameter="sms_es_connector.webhook_hmac_secret",
        help="Si se establece, se usará para verificar \
            la firma HMAC-SHA256 de la solicitud.",
    )

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        # Cargar la frecuencia actual del cron job
        cron = self.env.ref(
            "sms_es_connector.ir_cron_sms_queue_worker",
            raise_if_not_found=False,
        )
        if cron:
            res.update(sms_es_cron_frequency_minutes=cron.interval_number)
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        # Guardar la frecuencia en el cron job
        cron = self.env.ref(
            "sms_es_connector.ir_cron_sms_queue_worker",
            raise_if_not_found=False,
        )
        if cron:
            cron.write(
                {
                    "interval_number": self.sms_es_cron_frequency_minutes,
                    "interval_type": "minutes",
                }
            )

    @api.depends(
        "sms_es_api_url", "sms_es_webhook_token"
    )  # Añadir dependencia del token
    def _compute_dlr_url(self):
        """Calcula la URL del webhook que el usuario
        debe configurar en el proveedor."""
        config_params = self.env["ir.config_parameter"].sudo()
        base_url = config_params.get_param("web.base.url")
        token = self.sms_es_webhook_token or config_params.get_param(
            "sms_es_connector.webhook_token"
        )

        for settings in self:
            if base_url and token:
                settings.sms_es_dlr_url = (
                    f"{base_url}/sms_es_connector/webhook/dlr?token={token}"
                )
            elif not base_url:
                settings.sms_es_dlr_url = (
                    "La 'web.base.url' del sistema no está configurada."
                )
            else:
                settings.sms_es_dlr_url = "Guarde la configuración para \
                    generar el token y la URL completa."
