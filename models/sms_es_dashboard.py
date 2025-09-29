# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import timedelta

class SmsDashboard(models.Model):
    _name = 'sms_es.dashboard'
    _description = 'Dashboard de KPIs de SMS'

    name = fields.Char(default="Dashboard") # Campo dummy para que el modelo funcione

    # --- KPIs ---
    total_sent = fields.Integer(compute='_compute_kpis', string="Total Enviados (API)")
    total_delivered = fields.Integer(compute='_compute_kpis', string="Entregados")
    total_undelivered = fields.Integer(compute='_compute_kpis', string="No Entregados")
    total_failed = fields.Integer(compute='_compute_kpis', string="Fallidos (API + Rechazados)")
    delivery_rate = fields.Float(compute='_compute_kpis', string="Tasa de Entrega (%)", group_operator="avg")

    # --- Gráficos (controlados por la vista) ---
    message_count_by_state = fields.Char(string="Mensajes por Estado")
    messages_over_time = fields.Char(string="Historial de Envíos")
    
    @api.depends('name')
    def _compute_kpis(self):
        message_model = self.env['sms_es.message']
        for record in self:
            # Estados finales para el cálculo de la tasa de entrega
            final_states = ['delivered', 'undelivered', 'rejected']
            
            # Conteo de mensajes por estado
            record.total_sent = message_model.search_count([('state', 'not in', ['draft', 'queued', 'api_failed'])])
            record.total_delivered = message_model.search_count([('state', '=', 'delivered')])
            record.total_undelivered = message_model.search_count([('state', '=', 'undelivered')])
            record.total_failed = message_model.search_count([('state', 'in', ['api_failed', 'rejected'])])
            
            # Cálculo de la tasa de entrega
            total_final = message_model.search_count([('state', 'in', final_states)])
            if total_final > 0:
                record.delivery_rate = (record.total_delivered / total_final) * 100
            else:
                record.delivery_rate = 0.0