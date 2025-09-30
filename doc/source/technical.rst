********************
Documentación Técnica
********************

Esta sección detalla la arquitectura, el diseño técnico y las guías de extensión del módulo **SMS España Connector**. Está dirigida a desarrolladores y administradores de sistemas.

.. contents:: Tabla de Contenidos
   :local:

Arquitectura General
====================

El módulo está diseñado siguiendo un patrón robusto y desacoplado para garantizar la escalabilidad y la facilidad de mantenimiento. Los componentes principales son:

- **Cliente API (`models/sms_es_client.py`)**: Una clase Python pura (no un modelo de Odoo) que encapsula toda la lógica de comunicación con la API del proveedor de SMS. Se encarga de construir los payloads JSON, manejar la autenticación, enviar las peticiones HTTP y procesar las respuestas, incluyendo una lógica de reintentos para errores transitorios (como throttling o errores de servidor).

- **Modelos de Datos Principales**:
  - `sms_es.message`: El modelo central que representa un único mensaje SMS. Almacena el contenido, remitente, receptor, el estado del ciclo de vida y las referencias al registro de origen (ej., un Contacto o una Factura).
  - `sms_es.queue_job`: Gestiona la cola de envíos. Cada registro representa un intento de envío para un `sms_es.message`. Contiene la lógica de reintentos, backoff exponencial y el estado del trabajo en sí (pendiente, fallido, etc.).
  - `sms_es.dlr_event`: Almacena cada evento de informe de entrega (DLR) recibido desde el webhook del proveedor. Mantiene un historial detallado del viaje de un mensaje después de ser enviado.
  - `res.config.settings`: Extiende el modelo de configuración de Odoo para almacenar de forma centralizada todas las credenciales y ajustes del módulo.

- **Cola de Envío Asíncrona**:
  - El sistema utiliza un **Cron Job** (`ir.cron`) de Odoo que se ejecuta a intervalos configurables.
  - Este cron job llama al método `_process_sms_queue` del modelo `sms_es.queue_job`.
  - Este método procesa los trabajos pendientes en lotes, asegurando que los envíos masivos no bloqueen la interfaz de usuario y se gestionen de forma eficiente en segundo plano.

- **Controlador de Webhook (`controllers/main.py`)**:
  - Define un endpoint HTTP público (`/sms_es_connector/webhook/dlr`).
  - Está diseñado para recibir las peticiones POST (en formato JSON) que envía el proveedor de SMS con los informes de estado de entrega (DLRs).
  - Incluye capas de seguridad para validar las peticiones mediante un token en la URL y, opcionalmente, una firma HMAC-SHA256.

- **Asistente de Envío (`wizards/sms_compose_wizard.py`)**:
  - Un modelo transitorio que proporciona la interfaz de usuario (pop-up) para componer y enviar SMS.
  - Se invoca desde diferentes modelos base (Contactos, Ventas, etc.) a través de acciones de servidor (`ir.actions.act_window`).


Flujo de Datos del Envío de un SMS
==================================

El ciclo de vida de un mensaje sigue estos pasos:

1.  **Creación**: Un usuario selecciona registros (ej., Contactos) y utiliza la acción "Enviar SMS es".
2.  **Asistente**: Se abre el `sms_es.compose.wizard`. El usuario redacta el mensaje y hace clic en "Enviar".
3.  **Generación de Mensajes**: El método `action_send_sms` del asistente itera sobre los registros seleccionados. Para cada uno, crea un nuevo registro en `sms_es.message` con el estado inicial `'draft'`.
4.  **Encolado**: El asistente llama al método `action_queue_sms` de los mensajes recién creados.
5.  **Deduplicación**: `action_queue_sms` primero verifica si ya se ha enviado un mensaje idéntico (mismo remitente, receptor y texto) para evitar duplicados. Si es un duplicado, el mensaje se marca como `'cancelled'`.
6.  **Creación del Trabajo**: Si no es un duplicado, se crea un registro en `sms_es.queue_job` para cada mensaje, y el estado del mensaje se actualiza a `'queued'`.
7.  **Procesamiento del Cron**: El cron job se ejecuta y llama a `_process_sms_queue`.
8.  **Ejecución del Trabajo**: El worker encuentra los trabajos pendientes, los marca como `'in_progress'` y utiliza el `SmsEsClient` para enviar el SMS a la API externa.
9.  **Respuesta de la API**:
    - **Éxito**: El estado del mensaje se actualiza a `'api_sent'`, y el trabajo en la cola se marca como `'success'`.
    - **Fallo**: El método `_handle_send_failure` gestiona el error. Si quedan reintentos, se reprograma el trabajo para más tarde. Si no, el trabajo se marca como `'failed'` y el mensaje como `'api_failed'`.

Flujo de Datos del Informe de Entrega (DLR)
===========================================

1.  **Recepción**: El proveedor de SMS envía una petición POST al endpoint `/sms_es_connector/webhook/dlr`.
2.  **Validación de Seguridad**: El controlador primero valida el token de la URL y la firma HMAC (si está configurada). Si la validación falla, devuelve un error `401 Unauthorized` o `403 Forbidden`.
3.  **Parseo**: El cuerpo JSON de la petición se decodifica.
4.  **Conciliación**: El controlador busca el registro `sms_es.message` correspondiente. La búsqueda se prioriza de la siguiente manera:
    a. Por el `odoo_message_id` enviado en el campo `custom` de la petición original.
    b. Como fallback, por el `msgId` (UUID de la API) devuelto por el proveedor.
5.  **Actualización de Estado**: Si se encuentra el mensaje, su estado se actualiza según el evento del DLR (ej., `'DELIVERED'` actualiza el estado a `'delivered'`).
6.  **Creación de Evento**: Se crea un nuevo registro en `sms_es.dlr_event` para almacenar todos los detalles del DLR, creando un historial auditable.
7.  **Respuesta**: Se devuelve un estado `200 OK` al proveedor para confirmar que el DLR ha sido procesado y que no debe volver a enviarlo.

Guía de Extensión y Personalización
====================================

El módulo ha sido diseñado para ser fácilmente extensible.

Añadir Soporte para un Nuevo Modelo (Ej. `project.task`)
--------------------------------------------------------

Para permitir el envío de SMS desde el modelo `project.task`, siga estos pasos:

1.  **Extender `sms_es.message`**:
    Añada un campo `Many2one` a `project.task` en el modelo `sms_es.message` para crear la relación.

    .. code-block:: python

       # en models/sms_es_message.py
       class SmsEsMessage(models.Model):
           _inherit = 'sms_es.message'
           
           project_task_id = fields.Many2one('project.task', string='Tarea del Proyecto')

2.  **Extender el Asistente para obtener el número**:
    Hereda del modelo `sms_es.compose.wizard` y extiende el método `_get_recipient_number` para que sepa cómo encontrar un número de teléfono en un registro de `project.task`.

    .. code-block:: python
       
       # en un nuevo archivo, ej. models/project_task.py
       class SmsComposeWizard(models.TransientModel):
           _inherit = 'sms_es.compose.wizard'

           def _get_recipient_number(self, record):
               if self.res_model == 'project.task':
                   # Lógica para encontrar el número, ej., a través del cliente de la tarea
                   if record.partner_id:
                       return record.partner_id.mobile or record.partner_id.phone
                   return None
               return super(SmsComposeWizard, self)._get_recipient_number(record)

3.  **Añadir la Acción a la Vista**:
    Crea un archivo XML para añadir la acción de "Enviar SMS es" a las vistas de lista y formulario de `project.task`.

    .. code-block:: xml
       
       <!-- en un nuevo archivo, ej. views/project_task_views.xml -->
       <record id="action_send_sms_project_task" model="ir.actions.act_window">
           <field name="name">Enviar SMS es</field>
           <field name="res_model">sms_es.compose.wizard</field>
           <field name="view_mode">form</field>
           <field name="target">new</field>
           <field name="binding_model_id" ref="project.model_project_task"/>
           <field name="binding_view_types">list,form</field>
       </record>