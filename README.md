PAYOMAPEO! CREA MAPAS TOPOGRÁFICOS DE NUESTRO REINO PLANO CON LA DIOPTRA DIGITAL!

 Este es un proyecto para hacer mediciones en terreno mediante ángulos con un telescopio. Porque la Tierra NO es una pelota como nos han dicho y vamos a medirla!

 La idea es ir al campo y hacer mediciones desde puntos concretos establecidos, hacia puntos concretos que observemos.

 Primero pondremos el telescopio en terreno lo más nivelado posible, encenderemos la dioptra digital y buscaremos ponerlo con la inclinación a cero. Se puede conectar vía Wifi del ESP32 al servidor que muestra la pantalla oled, desde ahí tendremos acceso a todas las funciones, si no, podemos anotar a mano los datos de la pantalla oled para cada punto observado.

 Desde la web, una vez que tengamos el telescopio con inclinación cero presionamos el botón "Guardar distancia al suelo", esto guardará la distandia que hay desde el centro de la retícula hasta el suelo para tener el dato de la altura del observador.

 Después, apuntamos hacia el punto que queramos, le ponemos un nombre al punto observado y presionamos el botón para guardar los datos de ese punto. Abajo del todo se actualizará una lista con los puntos que vayamos anotando, también puedes descargarlo en formato CSV.

 Una vez que hayas recopilado datos en el terreno puedes introducirlos en blender mediante el addon que acompaño aquí.

¿CÓMO FUNCIONA EL ADDON DE BLENDER?
--------------------------
 Con el addon puedes volcar los datos recogidos en el campo y establecer distancias automáticamente hacia los puntos observados.

 Primero creas la estación principal desde la que harás observaciones y luego vas creando los puntos observados dependiendo de los ángulos recogidos. Si no se establece una distancia concreta aparecerá un rayo de visión "infinito" el cual quedará ahí hasta que otro rayo lo intersecte y entonces aparecerán automáticamente las distancias calculadas por trigonometría.

 Los puntos observados también pueden convertirse en puntos de observación simplemente eligiéndolos por su nombre en el desplegable. De esta manera podemos ir formando una red y mapear distancias tan grandes como queramos.

 Se puede aplicar o no la declinación magnética, establecer un margen de error para las intersecciones de los rayos o también crear líneas manualmente eligiendo dos puntos.

HARDWARE
--------------------------
 Consta de una retícula para adaptar a un telescopio en el archivo "RETICULA DIOPTRA.STL" (deberás revisar las medidas de la punta de tu telescopio para adaptar el archivo STL a ellas).

 Dentro de la caja tendrás que acomodar la electrónica teniendo en cuenta de pegar el MPU6050 lo más horizontal posible en una de las "lejas" que hay dentro de la carcasa. Trata de que el magnetrómetro también esté bien alineado. Si no puedes mantener la orientación por defecto de estos módulos por cuestiones de montaje deberás modificar el código teniendo en cuenta tu configuración, he dejado anotaciones en las líneas correspondientes.

También debes poner tus datos propios para la red Wifi y la contraseña.

LISTA DE COMPONENTES
----------------------------------

-ESP32 C3 Supermini (procesador)
-MPU6050 (acelerómetro/ giroscopio de 3 ejes)
-GY-271 (magnetómetro de 3 ejes)
-BMP280 (sensor de altitud/ presión/ temperatura)
-Pantalla Oled 0.96"
-VL53L0X (sensor de distancia)

-Retícula STL y su tapa (adjuntos) 
-4 tornillos M2x6
-4 tuercas de inserción M2 

SOFTWARE
--------------------------

-Código .ino para el ESP32 C3
-Addon para Blender

