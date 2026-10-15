# Implementación de stored procedures usando una API REST para controlar un vehículo a control remoto
Este programa controla las llamadas a los prcoedimientos dentro de un esquema de base de datos.
Dicho esquema se encarga de guardar los registros de los movimientos realizados por un carro a control remoto manejado a través de WiFi con una ESP8266.
La base de datos guarda, entre otras cosas, el vehículo en sí, es decir, su modelo, id, descripción, etcétera.
También guarda los movimietnos asociados a ese vehículo y el código que les representa, como Avanzar, Retroceder, Girar a la izquierda o derecha, entre otros. Existe una tabla llamada demos, las cual almacena una demostración de varios movimietos que se ejecutan en sucesión.

En general los procedimientos se encargan de controlar qué comandos se envían, actualizan el historial de comandos que se han ejecutado, permiten guardar, editar o elminar comandos, entre otras cosas más. 

La aplicación usa una REST API con métodos HTTP para controlar dichos procedimientos desde un cliente web.
La mayoría de procedimientos se ejecutan de esta forma, sin embargo, en el caso de los demos, estos se ejecutan a través de un websocket que va mostrando el estado actual del demo, es decir, en qué comando se encuentra.