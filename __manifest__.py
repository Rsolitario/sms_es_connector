# -*- coding: utf-8 -*-
{
    'name': 'SMS España Connector',
    'version': '1.0.0',
    'author': 'Rafael Solitario',
    'category': 'Marketing/SMS Marketing',
    'summary': 'Conector para envío de SMS a través de proveedores españoles.',
    'description': """
        Este módulo proporciona una base para conectar Odoo con APIs de proveedores de SMS en España.
        - Gestiona el envío de mensajes SMS.
        - Sistema de cola para envíos masivos.
        - Seguimiento de los estados de entrega (DLR).
    """,
    'depends': [
        'base',
        'crm',
        'sale_management',
        'account',
    ],
    'icon': 'sms_es_connector/static/description/icon.png',
    'data': [
        'security/ir.model.access.csv', # Asegúrate de crear este archivo
        #'views/sms_es_connector_menus.xml',        
        'data/sms_es_connector_cron.xml',
        'data/sms_es_dashboard_data.xml',
        # Asistentes (Wizards)
        'views/sms_es_dlr_event_views.xml',
        'views/sms_es_message_views.xml',
        'views/sms_es_dashboard_views.xml',
        'wizards/sms_compose_wizard_views.xml',
        'views/res_partner_views.xml',
        'views/crm_lead_views.xml',
        'views/sale_order_views.xml',
        'views/account_move_views.xml',
        'views/sms_es_connector_settings_views.xml',
        
    ],
    'post_init_hook': '_post_init_hook',
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}