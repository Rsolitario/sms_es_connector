.. _description:
Descripción
(Fragmento: DESCRIPTION.md)
Este módulo, SMS España Connector, integra Odoo con proveedores de SMS españoles para permitir la gestión completa de campañas de marketing y notificaciones por SMS directamente desde la plataforma.
Sus características principales incluyen:
Envío Asíncrono: Utiliza una cola de trabajos (queue jobs) y un cron para procesar los envíos en segundo plano, garantizando que la interfaz de usuario no se bloquee durante envíos masivos.
Seguimiento de Entregas (DLR): Implementa un webhook para recibir informes de estado de entrega (DLR) del proveedor, actualizando el estado de cada mensaje en tiempo real (ej. entregado, fallido, no entregado).
Asistente de Envío Unificado: Proporciona un asistente emergente accesible desde los principales modelos de Odoo (Contactos, Ventas, Facturas, CRM) para componer y enviar SMS de forma fácil y rápida.
Dashboard de Analíticas: Ofrece un panel visual con indicadores clave (KPIs) como el total de enviados, entregados, fallidos y la tasa de entrega para un seguimiento efectivo del rendimiento.
Configuración Centralizada: Todos los ajustes, credenciales de API y opciones de envío se gestionan de forma centralizada.
Seguridad Robusta: Protege el endpoint del webhook mediante un token secreto y una firma HMAC-SHA256 opcional para garantizar la autenticidad de las notificaciones.