# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)


class SmsComposeWizard(models.TransientModel):
    _name = "sms_es.compose.wizard"
    _description = "Asistente para Componer y Enviar SMS"

    # Campos para identificar los registros de origen
    res_model = fields.Char("Modelo de Origen", readonly=True)
    res_ids_str = fields.Char("IDs de Origen", readonly=True)
    # Usamos un string para evitar problemas de tamaño

    # Campos del mensaje
    sender = fields.Char(string="Remitente", required=True)
    text = fields.Text(string="Mensaje", required=True)
    dcs = fields.Selection(
        [
            ("gsm", "GSM (Estándar, 160 caracteres)"),
            ("ucs", "UCS-2 (Unicode, 70 caracteres)"),
        ],
        string="Codificación",
        required=True,
    )

    # Campos de opciones avanzadas (visibilidad controlada)
    config_use_flash = fields.Boolean(readonly=True)
    use_flash = fields.Boolean(string="Enviar como Mensaje Flash")

    config_use_validate_period = fields.Boolean(readonly=True)
    use_validate_period = fields.Boolean(
        string="Establecer Periodo de Validez"
    )
    validate_period_minutes = fields.Integer(string="Validez (minutos)")

    @api.model
    def default_get(self, fields_list):
        # Asegúrate de tener 'import logging' y '_logger = ...'
        # al principio del archivo
        _logger.info(
            "WIZARD: Ejecutando default_get para \
                     el asistente de envío..."
        )

        res = super(SmsComposeWizard, self).default_get(fields_list)

        # --- MÉTODO DIRECTO PARA DIAGNÓSTICO ---
        config_param = self.env["ir.config_parameter"].sudo()

        default_sender = config_param.get_param(
            "sms_es_connector.default_sender", "VALOR_NO_ENCONTRADO"
        )
        _logger.info(
            f"WIZARD: Valor de 'sender' leído directamente: '{default_sender}'"
        )

        res.update(
            {
                "sender": (
                    default_sender
                    if default_sender != "VALOR_NO_ENCONTRADO"
                    else ""
                ),
                "dcs": config_param.get_param("sms_es_connector.dcs", "gsm"),
                "config_use_flash": config_param.get_param(
                    "sms_es_connector.use_flash", False
                ),
                "config_use_validate_period": config_param.get_param(
                    "sms_es_connector.use_validate_period", False
                ),
                "validate_period_minutes": int(
                    config_param.get_param(
                        "sms_es_connector.validate_period_minutes", 1440
                    )
                ),
            }
        )

        # Cargar el contexto (esta parte está bien)
        if self.env.context.get("active_model"):
            res["res_model"] = self.env.context["active_model"]
        if self.env.context.get("active_ids"):
            res["res_ids_str"] = ",".join(
                map(str, self.env.context["active_ids"])
            )

        return res

    def _get_recipient_number(self, record):
        """
        Intenta obtener el número de móvil/teléfono del registro.
        La lógica puede ser extendida según las necesidades.
        """
        # 1. Lógica específica para el propio modelo de Contacto (res.partner)
        if self.res_model == "res.partner":
            return record.mobile or record.phone

        # 2. Lógica específica para Leads/Oportunidades (crm.lead)
        if self.res_model == "crm.lead":
            # Prioridad 1: El móvil o teléfono del propio Lead
            if record.mobile:
                return record.mobile
            if record.phone:
                return record.phone
            # Prioridad 2: Si no tiene, buscar en el contacto asociado
            # (si existe)
            if record.partner_id:
                return record.partner_id.mobile or record.partner_id.phone
            return None  # No se encontró número

        # 3. Lógica genérica para otros modelos (Ventas, Facturas) que usan
        # partner_id
        if hasattr(record, "partner_id"):
            # Usamos getattr para acceder de forma segura a
            # 'partner_shipping_id',
            # que puede no existir. Si no existe, usamos partner_id.
            partner = (
                getattr(record, "partner_shipping_id", None)
                or record.partner_id
            )
            if partner:
                return partner.mobile or partner.phone

        return None

    def action_send_sms(self):
        self.ensure_one()
        if not self.res_ids_str:
            raise UserError("No se ha seleccionado ningún registro.")

        res_ids = [int(i) for i in self.res_ids_str.split(",")]
        records = self.env[self.res_model].browse(res_ids)

        all_messages = self.env["sms_es.message"]
        skipped_records = []

        for record in records:
            receiver_number = self._get_recipient_number(record)
            if not receiver_number:
                skipped_records.append(record.display_name)
                continue

            # Crear el registro del mensaje
            message_vals = {
                "name": f"SMS para {record.display_name}",
                "text": self.text,
                "sender": self.sender,
                "receiver": receiver_number,
                "state": "draft",
                # Relacionar el mensaje con su origen
                "res_id": record.id,
                "res_model": self.res_model,
            }
            # Añadir campos directos para acceso rápido si el modelo coincide
            if self.res_model == "res.partner":
                message_vals["partner_id"] = record.id
            elif self.res_model == "crm.lead":
                message_vals["lead_id"] = record.id
            elif self.res_model == "sale.order":
                message_vals["sale_order_id"] = record.id
            elif self.res_model == "account.move":
                message_vals["account_move_id"] = record.id

            new_message = self.env["sms_es.message"].create(message_vals)
            all_messages |= new_message

        if not all_messages:
            raise UserError(
                "No se pudo crear ningún mensaje. Verifique que los \
                siguientes registros tengan un número de teléfono o móvil:\n\n"
                + "\n".join(skipped_records)
            )

        # Poner todos los mensajes creados en la cola
        all_messages.action_queue_sms()

        if skipped_records:
            # Notificar al usuario si algunos registros no tenían número
            # (Esto se podría hacer con un pop-up más avanzado si se desea)
            _logger.warning(
                "No se pudo enviar SMS a los siguientes "
                "registros por falta de número: %s",
                ", ".join(skipped_records),
            )

        return {"type": "ir.actions.act_window_close"}
