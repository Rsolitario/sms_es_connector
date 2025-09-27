# /hooks.py
# -*- coding: utf-8 -*-

from odoo import api, SUPERUSER_ID
from odoo.tools import misc
import os
import logging

_logger = logging.getLogger(__name__)

# --- Bloque de importación compatible con múltiples versiones ---
try:
    from odoo import release
except ImportError:
    from odoo.tools import release

# ==============================================================================
# SECCIÓN DE AYUDANTES (HELPERS) - ESTAS FUNCIONES YA ESTÁN PERFECTAS
# ==============================================================================

def _configure_settings_view(env, odoo_version):
    """
    Encuentra la vista de ajustes 'placeholder' y la configura COMPLETAMENTE
    con la herencia y la arquitectura correctas para la versión de Odoo.
    """
    _logger.info("1/2: Configurando la vista de ajustes...")
    
    if odoo_version >= 14:
        arch_file = 'views/settings_arch_modern.xml'
    else:
        arch_file = 'views/settings_arch_legacy.xml'
    
    try:
        module_path = os.path.dirname(__file__)
        file_path = os.path.join(module_path, arch_file)
        
        with misc.file_open(file_path, 'r') as f:
            arch_content = f.read()

        view = env.ref('sms_es_connector.res_config_settings_view_form_inherit_sms_es_connector')
        parent_view = env.ref('base.res_config_settings_view_form')

        view.sudo().write({
            'inherit_id': parent_view.id,
            'arch': arch_content,
        })
        _logger.info(f"   -> Vista actualizada para heredar de '{parent_view.name}' y usar la arquitectura de '{arch_file}'.")

    except Exception as e:
        _logger.error("   -> No se pudo actualizar la arquitectura de la vista de ajustes: %s", e)


def _configure_cron_job(env, odoo_version):
    """
    Encuentra la tarea programada y establece los campos 'numbercall' / 'doall'
    según la versión de Odoo para garantizar la compatibilidad.
    """
    _logger.info("2/2: Configurando la tarea programada (cron)...")
    try:
        cron_job = env.ref('sms_es_connector.ir_cron_sms_queue_worker', raise_if_not_found=True)
        vals_to_write = {}

        if odoo_version <= 14:
            if 'numbercall' in cron_job._fields:
                vals_to_write['numbercall'] = -1
            if 'doall' in cron_job._fields:
                vals_to_write['doall'] = False
        else: # Para v15+
            if 'number_of_calls' in cron_job._fields:
                 vals_to_write['number_of_calls'] = -1
        
        if vals_to_write:
            cron_job.write(vals_to_write)
            _logger.info(f"   -> Tarea programada actualizada con los campos: {list(vals_to_write.keys())}.")
        else:
            _logger.info("   -> No se necesitaron cambios en la tarea programada para esta versión.")

    except ValueError:
        _logger.warning("   -> No se encontró el cron 'ir_cron_sms_queue_worker'.")

# ==============================================================================
# FUNCIÓN PRINCIPAL DEL HOOK (VERSIÓN UNIVERSAL Y CORRECTA)
# ==============================================================================

def _post_init_hook(*args):
    """
    Función principal universal que funciona en todas las versiones de Odoo.
    Usa *args para aceptar cualquier número de argumentos posicionales.
    """
    # --- Detectar cómo fue llamado el hook y obtener el 'env' ---
    if len(args) == 1 and isinstance(args[0], api.Environment):
        # Estamos en Odoo 15+
        env = args[0]
    elif len(args) == 2:
        # Estamos en Odoo 14- (o similar)
        cr, registry = args
        env = api.Environment(cr, SUPERUSER_ID, {})
    else:
        _logger.error("La firma del post_init_hook es desconocida. No se puede continuar.")
        return

    # --- A partir de aquí, el resto del código es el que ya tenías ---
    try:
        odoo_version = int(release.major_version.split('.')[0])
    except Exception:
        odoo_version = 16 # Fallback
        _logger.warning("No se pudo determinar la versión de Odoo, asumiendo v%s", odoo_version)
    
    _logger.info(f"== Ejecutando Post-Init Hook para 'sms_es_connector' en Odoo v{odoo_version} ==")
    
    _configure_settings_view(env, odoo_version)
    _configure_cron_job(env, odoo_version)
    
    _logger.info("== Post-Init Hook completado con éxito. ==")