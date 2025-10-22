.. _usage:

Usage
=====

Sending an SMS
--------------

The module allows you to send SMS messages in bulk from the main Odoo models:

#. Navigate to the list view of **Contacts**, **CRM Opportunities**, **Sales Orders**, or **Customer Invoices**.
#. Select one or more records.
#. Click on the **Action** menu and select the **Send SMS es** option.
#. In the pop-up window, compose the message and configure the sending options.
#. When you click **Send**, the messages are added to a queue to be processed in the background.

Tracking and Analysis
---------------------

The module provides several tools to monitor your mailings:

*   **Dashboard (SMS Marketing > Dashboard):**
    Offers a performance overview with KPIs such as Total Sent, Delivered, Not Delivered, Failed, and the Delivery Rate.

*   **Sent Messages (SMS Marketing > Sent Messages):**
    Displays a complete history of all SMS messages, with color codes to quickly identify their status (Green: Delivered, Orange: In progress, Red: Failed). You can click on any message to see its details and the full history of delivery events.

*   **Sending Queue (SMS Marketing > Sending Queue):**
    Allows you to monitor messages that are waiting to be processed by the worker, which is useful for diagnosing bulk sending flows.