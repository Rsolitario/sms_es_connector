# -*- coding: utf-8 -*-
import json
import logging
import requests
import time

from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Códigos de error específicos de la API de SMS.es
RC_THROTTLING_ERROR = 105


class SmsEsClient:
    """
    Cliente de API para interactuar con el servicio de SMS.es.
    Esta clase no es un modelo de Odoo, sino una clase de utilidad.
    """

    def __init__(self, env):
        """
        Inicializa el cliente cargando la configuración desde Odoo.
        :param env: El entorno de Odoo (self.env de un modelo).
        """
        self.env = env
        config_params = self.env["ir.config_parameter"].sudo()
        self.api_url = config_params.get_param("sms_es_connector.api_url")
        self.username = config_params.get_param(
            "sms_es_connector.api_username"
        )
        self.password = config_params.get_param(
            "sms_es_connector.api_password"
        )
        self.dlr_mask = int(
            config_params.get_param("sms_es_connector.dlr_mask", 19)
        )
        self.base_url = config_params.get_param("web.base.url")

        self.webhook_token = config_params.get_param(
            "sms_es_connector.webhook_token"
        )
        if self.base_url and self.webhook_token:
            self.dlr_url = f"{self.base_url}/sms_es_connector/\
                webhook/dlr?token={self.webhook_token}"
        else:
            self.dlr_url = None

        # Opciones avanzadas
        self.dcs = config_params.get_param("sms_es_connector.dcs", "gsm")
        self.use_flash = config_params.get_param("sms_es_connector.use_flash")
        self.use_validate_period = config_params.get_param(
            "sms_es_connector.use_validate_period"
        )
        self.validate_period_minutes = int(
            config_params.get_param(
                "sms_es_connector.validate_period_minutes", 1440
            )
        )

        if not all([self.api_url, self.username, self.password]):
            raise UserError(
                "La configuración de la API de SMS.es \
                    (URL, usuario, contraseña) no está completa."
            )

    def _build_payload(self, message_data):
        """
        Construye el diccionario del payload JSON
        a partir de los datos del mensaje.
        :param message_data: Diccionario con
        'receiver', 'text', 'sender', 'odoo_message_id'.
        :return: Diccionario listo para ser convertido a JSON.
        """
        payload = {
            "type": message_data.get("type", "text"),
            "auth": {
                "username": self.username,
                "password": self.password,
            },
            "sender": message_data["sender"],
            # E.164 sin el '+'
            "receiver": message_data["receiver"].lstrip("+"),
            "text": message_data["text"],
            "custom": {"odoo_message_id": message_data["odoo_message_id"]},
        }

        # Añadir parámetros si están definidos en la configuración
        if payload["type"] == "text":
            payload["dcs"] = self.dcs

        if self.dlr_mask and self.dlr_url:
            payload["dlrMask"] = self.dlr_mask
            payload["dlrUrl"] = self.dlr_url

        if self.use_flash:
            payload["flash"] = True

        if self.use_validate_period:
            payload["validatePeriodMinutes"] = self.validate_period_minutes

        return payload

    def send_sms(self, message_data, max_retries=3):
        """
        Envía un SMS, gestionando la construcción del
        payload y la lógica de reintentos.
        :param message_data: Diccionario con los datos del mensaje.
        :param max_retries: Número máximo de
        reintentos para errores transitorios.
        :return: Un diccionario con el resultado:
        {'status': 'success'/'failed', 'data': ..., 'error': ...}
        """
        try:
            payload = self._build_payload(message_data)
            payload_for_log = payload.copy()
            # payload_for_log['auth']['password'] =
            # '********' # Ocultar contraseña en logs
            _logger.info(
                "Enviando SMS. Payload: %s", json.dumps(payload_for_log)
            )
        except Exception as e:
            _logger.error("Error construyendo el payload del SMS: %s", e)
            return {
                "status": "failed",
                "error": {"code": -1, "message": f"Error de payload: {e}"},
            }

        attempts = 0
        while attempts < max_retries:
            attempts += 1
            try:
                headers = {"Content-Type": "application/json; charset=utf-8"}
                response = requests.post(
                    self.api_url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers=headers,
                    timeout=20,  # Timeout de 20 segundos
                )

                # --- Manejo de la respuesta HTTP ---

                # 202: Aceptado (Éxito)
                if response.status_code == 202:
                    _logger.info(
                        "SMS aceptado por la API. Respuesta: %s", response.text
                    )
                    return {"status": "success", "data": response.json()}

                # 420: Rechazado (Error del cliente)
                elif response.status_code == 420:
                    error_data = response.json().get("error", {})
                    error_code = error_data.get("code")
                    error_message = error_data.get(
                        "message", "Error desconocido"
                    )
                    _logger.warning(
                        "SMS rechazado (420) por la \
                            API. Código: %s, Mensaje: %s",
                        error_code,
                        error_message,
                    )

                    if error_code == RC_THROTTLING_ERROR:
                        _logger.info(
                            "Error de throttling (105). \
                                Reintentando en 1 segundo..."
                        )
                        time.sleep(1)
                        continue  # Reintentar
                    else:
                        # Error definitivo, no reintentar
                        return {
                            "status": "failed",
                            "error": {
                                "code": error_code,
                                "message": error_message,
                            },
                        }

                # 5xx: Error del servidor
                elif 500 <= response.status_code < 600:
                    _logger.error(
                        "Error del servidor de la API (%s).\
                              Reintentando en 1 minuto...",
                        response.status_code,
                    )
                    time.sleep(60)
                    continue  # Reintentar

                # Otros códigos de error inesperados
                else:
                    _logger.error(
                        "Respuesta inesperada de la \
                            API. Código: %s, Respuesta: %s",
                        response.status_code,
                        response.text,
                    )
                    return {
                        "status": "failed",
                        "error": {
                            "code": response.status_code,
                            "message": response.text,
                        },
                    }

            except requests.exceptions.RequestException as e:
                _logger.error(
                    "Error de conexión con la API de SMS:\
                          %s. Reintentando en 1 minuto...",
                    e,
                )
                if attempts < max_retries:
                    time.sleep(60)
                continue  # Reintentar

        _logger.error(
            "El envío del SMS ha fallado después de %d intentos.", max_retries
        )
        return {
            "status": "failed",
            "error": {
                "code": -1,
                "message": f"Falló después de {max_retries} reintentos.",
            },
        }
