# -*- coding: utf-8 -*-
from odoo import models, fields

try:
    JsonField = fields.Json
except AttributeError:
    JsonField = fields.Text

class SmsEsDlrEvent(models.Model):
    _name = 'sms_es.dlr_event'
    _description = 'Evento de Estado de Entrega (DLR)'
    _order = 'create_date desc'

    message_id = fields.Many2one('sms_es.message', string='Mensaje SMS', required=True, ondelete='cascade')
    event = fields.Char(string='Evento', index=True)
    errorCode = fields.Integer(string='Código de Error', default=0)
    errorMessage = fields.Char(string='Mensaje de Error')
    partNum = fields.Integer(string='Número de Parte')
    numParts = fields.Integer(string='Total de Partes')
    sendTime = fields.Float(string='Tiempo de Envío (s)')
    dlrTime = fields.Float(string='Tiempo de DLR (s)')
    custom = JsonField(string='Datos Personalizados')