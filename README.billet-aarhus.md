# Pretix patches for billet.aarhus.dk

* Don't create a team for managing an event (src/pretix/control/views/main.py)
* Allow users with permission "can_view_orders" to send out emails (src/pretix/plugins/sendmail/{signals,views}.py)
