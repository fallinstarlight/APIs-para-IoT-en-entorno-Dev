# API de control de un vehículo IoT
Esta aplicación de Python se encarga de recibir solicitudes relacionadas al control de un vehículo que funciona a través de internet.
Cuenta con 21 endpoints que reflejan 21 procedimientos almacenados de una base de datos MySQL. Estos procedimientos se encargan de todo tipo de operaciones CRUD relacionadas al control de este vehículo, como la definición del vehículo en sí, los comandos que se puedan ejecutar en él, el control de demos y el registro de estados de movimiento dentro de un historial.
La parte más importante de esta API es la del control de estado, un endpoint en el que se envía un comando usando un código numérico que lo identifica. Un websocket se comunicará entonces a un microcontrolador ESP y, con base en el comando recibido, hará que el vehículo ejecute acciones diferentes.
La comunicación con esta API se hace a través de métodos HTTP con cuerpos en formato JSON.
Este repo cuenta además con el firmware usado en la ESP para recibir información del websocket de la API y con ello ejecutar los comandos en el vehículo físico. 
