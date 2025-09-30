***************
Guía de Usuario
***************

Bienvenido a la guía de usuario del módulo **SMS España Connector**. Este documento explica en detalle cómo instalar, configurar y utilizar todas las funcionalidades del módulo para gestionar sus campañas de marketing por SMS directamente desde Odoo.

.. contents:: Tabla de Contenidos
   :local:

Instalación
===========

Para instalar el módulo, siga estos sencillos pasos:

1.  Acceda a su instancia de Odoo como administrador.
2.  Navegue al menú de **Apps**.
3.  En la barra de búsqueda, elimine el filtro "Apps" por defecto y busque "SMS España Connector".
4.  Cuando aparezca la tarjeta del módulo, haga clic en el botón **Instalar**.

Una vez completada la instalación, un nuevo menú principal llamado **SMS Marketing** aparecerá en su panel de Odoo.

Configuración Inicial
=====================

Antes de poder enviar mensajes, es fundamental configurar correctamente la conexión con su proveedor de SMS.

1.  Navegue a **SMS Marketing > Ajustes SMS España**.
2.  La pantalla de configuración está dividida en varias secciones:

Configuración de la API
-----------------------
Estos son los datos de autenticación para conectar con su proveedor.

- **API Username**: Su nombre de usuario de la API, proporcionado por el proveedor de SMS.
- **API Password**: La contraseña o clave secreta asociada a su cuenta de API.
- **URL del Endpoint de Envío**: La URL específica a la que Odoo enviará las peticiones para enviar SMS. Consulte la documentación de su proveedor para obtener la URL correcta.
- **Remitente por Defecto**: El nombre o número de teléfono que aparecerá como remitente de los SMS. Puede ser un nombre alfanumérico (ej., "MiEmpresa") o un número de teléfono.

Configuración de Entrega (DLR)
------------------------------
Esta sección es crucial para que Odoo pueda recibir actualizaciones sobre el estado de los mensajes enviados (si fueron entregados, fallaron, etc.).

- **URL del Webhook DLR**: Esta es la URL **que debe copiar** y pegar en el panel de configuración de su proveedor de SMS. Es la dirección a la que el proveedor enviará las notificaciones de estado de entrega.
- **Máscara DLR**: Un valor numérico que le dice al proveedor qué tipos de notificaciones de estado desea recibir. El valor por defecto (`19`) es el recomendado, ya que solicita notificaciones para mensajes entregados, no entregados y rechazados.

Seguridad del Webhook DLR
-------------------------
Para proteger su sistema de peticiones no autorizadas, el webhook utiliza dos niveles de seguridad:

- **Webhook Secret Token**: Un token único generado por Odoo. Se añade automáticamente a la URL del webhook.
- **Webhook HMAC Secret**: (Opcional, pero recomendado) Una clave secreta adicional que puede configurar. Si la establece, el proveedor debe usar esta clave para generar una firma digital en cada petición de DLR. Odoo verificará esta firma para garantizar que la petición es auténtica.

Opciones Avanzadas y Worker
----------------------------
Aquí puede ajustar el comportamiento de los envíos:

- **Activar Mensajes Flash**: Si se marca, los SMS se enviarán como "mensajes flash", que aparecen directamente en la pantalla del destinatario y no se guardan en su bandeja de entrada.
- **Activar Periodo de Validez**: Permite definir un tiempo máximo (en minutos) durante el cual la red intentará entregar el mensaje. Si el destinatario no está disponible durante ese tiempo, el mensaje expirará.
- **Codificación de Datos (DCS)**: Permite elegir entre ``GSM`` (para texto estándar, hasta 160 caracteres) y ``UCS-2`` (para caracteres especiales y emojis, hasta 70 caracteres).
- **Frecuencia del Worker**: Define cada cuántos minutos se procesará la cola de envíos. Un valor bajo (ej., `1` minuto) es ideal para envíos rápidos.


Envío de un SMS
===============

El módulo permite enviar SMS de forma masiva desde los principales modelos de Odoo a través del menú "Acción".

1.  Navegue a la vista de lista de uno de los siguientes modelos:
    - **Contactos**
    - **CRM > Oportunidades**
    - **Ventas > Pedidos de Venta**
    - **Facturación > Facturas de Cliente**
2.  Seleccione uno o varios registros marcando las casillas de verificación.
3.  Haga clic en el menú **Acción**.
4.  Seleccione la opción **Enviar SMS es**.

Se abrirá una ventana emergente donde podrá:

- **Verificar el Remitente**: Por defecto, se usará el configurado en los ajustes.
- **Escribir el Mensaje**: Redacte el contenido del SMS.
- **Elegir la Codificación**: Asegúrese de que coincida con el tipo de caracteres que está utilizando.
- **Configurar Opciones Avanzadas**: Si están activadas en los ajustes, puede decidir si usar "Mensaje Flash" o un "Periodo de Validez" para este envío en particular.

Al hacer clic en **Enviar**, los mensajes no se envían inmediatamente, sino que se añaden a una cola para ser procesados en segundo plano, garantizando que el sistema no se ralentice.

Seguimiento y Análisis
======================

El módulo proporciona varias herramientas para monitorizar sus envíos.

Dashboard
---------
El dashboard, accesible desde **SMS Marketing > Dashboard**, le proporciona una visión general del rendimiento de sus campañas con indicadores clave (KPIs):

- **Total Enviados**: El número de mensajes que han sido aceptados por la API de su proveedor.
- **Entregados**: El número de mensajes confirmados como entregados al destinatario.
- **No Entregados**: Mensajes que no pudieron ser entregados (ej., el teléfono estaba apagado).
- **Fallidos**: Mensajes rechazados por la API o por la red.
- **Tasa de Entrega**: Un gráfico de progreso que muestra el porcentaje de mensajes entregados sobre el total de mensajes que alcanzaron un estado final.

Mensajes Enviados
-----------------
En **SMS Marketing > Mensajes Enviados**, encontrará un historial completo de todos los SMS. La lista utiliza códigos de colores para identificar rápidamente el estado de cada mensaje:

- **Verde**: Entregado con éxito.
- **Naranja/Amarillo**: En proceso (en cola, enviando, etc.).
- **Rojo**: Fallido o no entregado.

Puede hacer clic en cualquier mensaje para ver sus detalles, incluyendo el historial completo de los eventos de entrega (DLRs) recibidos del proveedor.

Cola de Envío
-------------
El menú **SMS Marketing > Cola de Envío** muestra todos los mensajes que están esperando ser procesados por el worker. Es útil para supervisar el flujo de envíos masivos y diagnosticar posibles retrasos.