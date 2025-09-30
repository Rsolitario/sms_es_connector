# -*- coding: utf-8 -*-
from odoo import models, fields, api
import uuid
import logging

_logger = logging.getLogger(__name__)

# Estados que consideramos 'finales' o 'enviados con éxito' para la deduplicación
DUPLICATION_CHECK_STATES = ['api_sent', 'dlr_buffered', 'dlr_sent_to_smsc', 'delivered', 'undelivered', 'rejected']

# Estructura para compatibilidad multi-versión
try:
    from odoo.tools.sql import column_exists, create_column
except ImportError:
    # Para versiones anteriores a Odoo 16
    from odoo.addons.base.models.ir_model import column_exists, create_column

class SmsEsMessage(models.Model):
    _name = 'sms_es.message'
    _description = 'Mensaje SMS'

    name = fields.Char(string='Descripción', required=True, index=True)
    text = fields.Text(string='Contenido del Mensaje', required=True)
    sender = fields.Char(string='Remitente', required=True)
    receiver = fields.Char(string='Receptor', required=True)
    msg_id = fields.Char(string='UUID de la API', readonly=True, index=True, default=lambda self: str(uuid.uuid4()))
    num_parts = fields.Integer(string='Número de Partes', default=1)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('queued', 'En Cola'),
        ('sending', 'Enviando'),
        ('api_sent', 'Enviado a la API'),
        ('api_failed', 'Fallo en la API'),
        ('dlr_buffered', 'DLR Buffered'),
        ('dlr_sent_to_smsc', 'DLR Enviado a SMSC'),
        ('delivered', 'Entregado'),
        ('undelivered', 'No Entregado'),
        ('rejected', 'Rechazado'),
        ('cancelled', 'Cancelado'),
    ], string='Estado', default='draft', required=True, index=True)

    # Campos genéricos para relación polimórfica
    res_id = fields.Integer(string='ID del Registro de Origen')
    res_model = fields.Char(string='Modelo de Origen')

    # Campos Many2one directos para acceso rápido
    partner_id = fields.Many2one('res.partner', string='Cliente')
    lead_id = fields.Many2one('crm.lead', string='Oportunidad/Lead')
    sale_order_id = fields.Many2one('sale.order', string='Pedido de Venta')
    account_move_id = fields.Many2one('account.move', string='Factura')

    # relaciones para poder mostrar los eventos DLR en el formulario del mensaje
    dlr_event_ids = fields.One2many(
        'sms_es.dlr_event',
        'message_id',
        string="Historial de Entrega (DLR)"
    )

    # ====================================================== #
    # MÉTODO PARA VALORES POR DEFECTO AL CREAR MANUALMENTE     #
    # ====================================================== #
    @api.model
    def default_get(self, fields_list):
        # Llama al método original para obtener los valores por defecto estándar
        res = super(SmsEsMessage, self).default_get(fields_list)
        
        # Solo si el campo 'sender' está siendo inicializado
        if 'sender' in fields_list:
            # Obtenemos el parámetro directamente de la configuración
            config_param = self.env['ir.config_parameter'].sudo()
            default_sender = config_param.get_param('sms_es_connector.default_sender')
            
            # Asignamos el valor al diccionario de resultados
            # El 'or ''' asegura que si no hay nada, se ponga una cadena vacía
            res['sender'] = default_sender or ''
            
        return res
    
    @api.model
    def _check_for_duplicates(self, sender, receiver, text):
        """
        Verifica si ya existe un mensaje idéntico que ha sido enviado o está en un estado final.
        :return: True si se encuentra un duplicado, False en caso contrario.
        """
        domain = [
            ('sender', '=', sender),
            ('receiver', '=', receiver),
            ('text', '=', text),
            ('state', 'in', DUPLICATION_CHECK_STATES)
        ]
        return self.search_count(domain) > 0

    def action_queue_sms(self):
        """
        Acción principal para encolar mensajes.
        Verifica duplicados y crea un trabajo en la cola si es necesario.
        Esta es la función que debe ser llamada desde otros módulos (CRM, Ventas, etc.).
        """
        messages_to_queue = self.browse()
        for message in self.filtered(lambda m: m.state == 'draft'):
            is_duplicate = self._check_for_duplicates(message.sender, message.receiver, message.text)
            
            if is_duplicate:
                _logger.info("SMS duplicado detectado para el receptor %s. Cancelando mensaje ID %d.", 
                             message.receiver, message.id)
                message.write({
                    'state': 'cancelled',
                    'name': f"[DUPLICADO] {message.name}"
                })
                continue
            
            messages_to_queue |= message

        if not messages_to_queue:
            return

        # Encolar todos los mensajes no duplicados
        for message in messages_to_queue:
            self.env['sms_es.queue_job'].create({
                'name': f"SMS para {message.receiver}: {message.name}",
                'message_id': message.id,
                # next_try_datetime se establece a now() por defecto,
                # para que el worker lo recoja en el siguiente ciclo.
            })
        
        messages_to_queue.write({'state': 'queued'})
        _logger.info("%d mensajes SMS han sido añadidos a la cola de envío.", len(messages_to_queue))
