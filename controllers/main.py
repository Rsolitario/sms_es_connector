# -*- coding: utf-8 -*-
import hashlib
import hmac
import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

# Mapeo de eventos DLR a estados del modelo sms_es.message
DLR_EVENT_TO_STATE = {
    "DELIVERED": "delivered",
    "UNDELIVERED": "undelivered",
    "REJECTED": "rejected",
    "BUFFERED": "dlr_buffered",
    "SENT_TO_SMSC": "dlr_sent_to_smsc",
}


class SmsEsWebhookController(http.Controller):

    @http.route(
        "/sms_es_connector/webhook/dlr",
        type="http",
        auth="none",
        methods=["POST"],
        csrf=False,
        save_session=False,
    )
    def handle_dlr_webhook(self, **kwargs):
        """
        Controlador para recibir y procesar los informes de entrega (DLR).
        """
        _logger.info(
            "Recibido DLR de SMS.es. Headers: %s, Body: %s",
            request.httprequest.headers,
            request.httprequest.data,
        )

        # --- 1. Verificación de Seguridad ---
        config = request.env["ir.config_parameter"].sudo()

        # a) Validar token en la URL
        received_token = kwargs.get("token")
        expected_token = config.get_param("sms_es_connector.webhook_token")
        if not received_token or not hmac.compare_digest(
            received_token, expected_token or ""
        ):
            _logger.warning(
                "Intento de acceso al webhook DLR con token inválido: %s",
                received_token,
            )
            return request.make_response("Unauthorized", status=401)

        # b) Validar firma HMAC (si está configurada)
        hmac_secret = config.get_param("sms_es_connector.webhook_hmac_secret")
        if hmac_secret:
            signature = request.httprequest.headers.get("X-SmsEs-Signature")
            if not signature:
                _logger.warning(
                    "Petición DLR recibida sin firma HMAC, \
                        pero hay un secreto configurado."
                )
                return request.make_response(
                    "Forbidden: Missing Signature", status=403
                )

            digest = hmac.new(
                hmac_secret.encode("utf-8"),
                msg=request.httprequest.data,
                digestmod=hashlib.sha256,
            ).hexdigest()

            if not hmac.compare_digest(digest, signature):
                _logger.warning("Firma HMAC inválida en la petición DLR.")
                return request.make_response(
                    "Forbidden: Invalid Signature", status=403
                )

        # --- 2. Parseo del DLR ---
        try:
            dlr_data = json.loads(request.httprequest.data.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            _logger.error("Error al decodificar el cuerpo del DLR JSON: %s", e)
            return request.make_response(
                "Bad Request: Malformed JSON", status=400
            )

        # --- 3. Conciliación con el Mensaje de Odoo ---
        message = request.env["sms_es.message"].sudo().browse()
        odoo_message_id = dlr_data.get("custom", {}).get("odoo_message_id")
        msg_id = dlr_data.get("msgId")

        # Prioridad 1: Buscar por odoo_message_id
        if odoo_message_id:
            try:
                message = (
                    request.env["sms_es.message"]
                    .sudo()
                    .browse(int(odoo_message_id))
                )
                if not message.exists():
                    message = (
                        request.env["sms_es.message"].sudo().browse()
                    )  # Reset if not found
            except (ValueError, TypeError):
                _logger.warning(
                    "odoo_message_id '%s' no es un entero válido.",
                    odoo_message_id,
                )

        # Prioridad 2 (Fallback): Buscar por msgId
        if not message and msg_id:
            message = (
                request.env["sms_es.message"]
                .sudo()
                .search([("msg_id", "=", msg_id)], limit=1)
            )

        if not message:
            _logger.warning(
                "No se encontró un mensaje en Odoo \
                    para el DLR recibido. odoo_id: %s, msg_id: %s",
                odoo_message_id,
                msg_id,
            )
            # Devolvemos 200 para que el proveedor
            # no reintente. El DLR es válido.
            return request.make_response("OK: Message not found", status=200)

        # --- 4. Actualización y Registro ---
        try:
            # a) Actualizar estado del mensaje principal
            event = dlr_data.get("event")
            new_state = DLR_EVENT_TO_STATE.get(event)
            if new_state:
                message.sudo().write({"state": new_state})
                _logger.info(
                    "Mensaje ID %d actualizado al estado\
                          '%s' por el evento DLR '%s'.",
                    message.id,
                    new_state,
                    event,
                )

            # b) Crear el registro del evento DLR
            dlr_vals = {
                "message_id": message.id,
                "event": event,
                "errorCode": dlr_data.get("errorCode"),
                "errorMessage": dlr_data.get("errorMessage"),
                "partNum": dlr_data.get("partNum"),
                "numParts": dlr_data.get("numParts"),
                "sendTime": dlr_data.get("sendTime"),
                "dlrTime": dlr_data.get("dlrTime"),
                "custom": (
                    json.dumps(dlr_data.get("custom"))
                    if dlr_data.get("custom")
                    else False
                ),
            }
            request.env["sms_es.dlr_event"].sudo().create(dlr_vals)
            _logger.info(
                "Evento DLR registrado para el mensaje ID %d.", message.id
            )

            # Confirmar la transacción
            request.env.cr.commit()

        except Exception as e:
            _logger.error(
                "Error al procesar y guardar el DLR para el mensaje ID %d: %s",
                message.id if message else 0,
                e,
            )
            request.env.cr.rollback()
            return request.make_response("Internal Server Error", status=500)

        return request.make_response("OK", status=200)
