#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <VL53L0X.h>
#include <QMC5883LCompass.h>
#include <Adafruit_BMP280.h>
#include <WiFi.h>
#include <WebServer.h>

// ------------------- CONFIGURACIÓN OLED -------------------
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);

// ------------------- SENSORES -------------------
VL53L0X tof;
Adafruit_MPU6050 mpu;
QMC5883LCompass compass;
Adafruit_BMP280 bmp;

// ------------------- PINES I2C ESP32-C3 SuperMini -------------------
#define SDA_PIN 8
#define SCL_PIN 9

// ------------------- WIFI -------------------
const char* ssid = "******"; //PON TU PROPIA RED WIFI <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< OJO AQUÍ!
const char* password = "******"; //PON LA CONTRASEÑA DE TU RED WIFI <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< OJO AQUÍ!
WebServer server(80);

// ------------------- VARIABLES GLOBALES -------------------
uint16_t distance;
float roll, pitch;
int heading;
float altitude;
float tempMPU, tempBMP, presionBMP;

// Variables para la funcionalidad web
uint16_t distanciaSueloCalibrada = 0;
String datosGuardados =
  "Punto,Distancia(mm),Inclinacion(deg),Alabeo(deg),Acimut(deg),Altitud(m),"
  "TempMPU(C),TempBMP(C),Presion(hPa),DistSueloCalibrada(mm)\n";

// ------------------- DECLARACIÓN DE FUNCIONES DEL SERVIDOR WEB -------------------
void handleRoot();
void handleCalibrar();
void handleGuardar();
void handleDownload();
void handleLimpiar();
void handleJSON();

// ------------------- FUNCIÓN PRINCIPAL DE LA PÁGINA WEB -------------------
void handleRoot() {
  String html = "<!DOCTYPE html><html><head><meta charset='utf-8'><meta name='viewport' "
                "content='width=device-width,initial-scale=1'>";
  html += "<title>PayoMapeo Web</title>";
  html += "<style>body{font-family:sans-serif;background-color:#f0f0f0;color:#333;"
          "max-width:800px;margin:0 auto;padding:15px;}"
          "h1,h2{color:#0056b3;}div{background-color:white;padding:20px;margin-bottom:20px;"
          "border-radius:8px;box-shadow:0 2px 4px rgba(0,0,0,0.1);} "
          "input[type='text'],input[type='submit']{padding:10px;margin-top:5px;border-radius:5px;"
          "border:1px solid #ccc;width:calc(100% - 22px);} "
          "input[type='submit']{background-color:#007bff;color:white;cursor:pointer;font-weight:bold;} "
          "a{text-decoration:none;display:inline-block;padding:10px 15px;background-color:#28a745;"
          "color:white;font-weight:bold;border-radius:5px;text-align:center;} "
          "pre{white-space:pre-wrap;word-wrap:break-word;background-color:#eee;padding:10px;border-radius:5px;}</style>";
  html += "</head><body>";
  html += "<h1>PayoMapeo Visor De Datos</h1>";

  // --- Lecturas en tiempo real ---
  html += "<div><h2>Lecturas en tiempo real</h2>";
  html += "<p><b>Distancia:</b> <span id='distancia'>--</span> mm</p>";
  html += "<p><b>Inclinación (Roll):</b> <span id='inclinacion'>--</span> &deg;</p>";
  html += "<p><b>Alabeo (Pitch):</b> <span id='alabeo'>--</span> &deg;</p>";
  html += "<p><b>Acimut:</b> <span id='acimut'>--</span> &deg;</p>";
  html += "<p><b>Altitud:</b> <span id='altitud'>--</span> m</p>";
  html += "<p><b>Temp. MPU6050:</b> <span id='tempmpu'>--</span> &deg;C</p>";
  html += "<p><b>Temp. BMP280:</b> <span id='tempbmp'>--</span> &deg;C</p>";
  html += "<p><b>Presión BMP280:</b> <span id='presion'>--</span> hPa</p></div>";

  // --- Calibración ---
  html += "<div><h2>Calibración</h2>";
  html += "<p>Apunta el telescopio nivelado al suelo y pulsa para guardar la distancia de referencia.</p>";
  html += "<p><b>Distancia al suelo guardada:</b> <span id='dist_calibrada'>--</span> mm</p>";
  html += "<form action='/calibrar' method='POST'><input type='submit' value='Guardar distancia al suelo'></form></div>";

  // --- Guardar punto ---
  html += "<div><h2>Guardar Punto Observado</h2>";
  html += "<form action='/guardar' method='POST'>";
  html += "<label for='punto'>Nombre del punto:</label><br>";
  html += "<input type='text' id='punto' name='punto' placeholder='Ej: Estrella Polar' required>";
  html += "<input type='submit' value='Guardar datos del punto'></form></div>";

  // --- Datos guardados ---
  html += "<div><h2>Datos Guardados</h2>";
  html += "<p>Los puntos que guardes aparecerán aquí. Puedes descargarlos como un archivo CSV.</p>";
  html += "<a href='/download' download='datos_telescopio.csv'>Descargar Datos (CSV)</a>";
  html += "<form action='/limpiar' method='POST' style='margin-top:10px;'><input type='submit' value='Limpiar todos los datos' style='background-color:#dc3545;'></form>";
  html += "<h3>Ficha de datos:</h3><pre>" + datosGuardados + "</pre></div>";

  // --- Script AJAX ---
  html += "<script>";
  html += "function actualizarDatos() {";
  html += "  fetch('/json')";
  html += "    .then(response => response.json())";
  html += "    .then(data => {";
  html += "      document.getElementById('distancia').innerText = data.distancia;";
  html += "      document.getElementById('inclinacion').innerText = data.inclinacion.toFixed(1);";
  html += "      document.getElementById('alabeo').innerText = data.alabeo.toFixed(1);";
  html += "      document.getElementById('acimut').innerText = data.acimut;";
  html += "      document.getElementById('altitud').innerText = data.altitud.toFixed(1);";
  html += "      document.getElementById('tempmpu').innerText = data.tempmpu.toFixed(1);";
  html += "      document.getElementById('tempbmp').innerText = data.tempbmp.toFixed(1);";
  html += "      document.getElementById('presion').innerText = data.presion.toFixed(1);";
  html += "      document.getElementById('dist_calibrada').innerText = data.distancia_suelo_calibrada;";
  html += "    })";
  html += "    .catch(error => console.error('Error al obtener datos:', error));";
  html += "}";
  html += "document.addEventListener('DOMContentLoaded', actualizarDatos);";
  html += "setInterval(actualizarDatos, 2000);";
  html += "</script>";

  html += "</body></html>";
  server.send(200, "text/html", html);
}

// ------------------- FUNCIONES WEB -------------------
void handleCalibrar() {
  distanciaSueloCalibrada = distance;
  server.sendHeader("Location", "/");
  server.send(303);
}

void handleGuardar() {
  if (server.hasArg("punto")) {
    String nombrePunto = server.arg("punto");
    String nuevaLinea = nombrePunto + "," + String(distance) + "," + String(roll, 1) + "," +
                        String(pitch, 1) + "," + String(heading) + "," + String(altitude, 1) + "," +
                        String(tempMPU, 1) + "," + String(tempBMP, 1) + "," + String(presionBMP, 1) +
                        "," + String(distanciaSueloCalibrada) + "\n";
    datosGuardados += nuevaLinea;
  }
  server.sendHeader("Location", "/");
  server.send(303);
}

void handleDownload() {
  server.sendHeader("Content-Disposition", "attachment; filename=datos_telescopio.csv");
  server.send(200, "text/csv", datosGuardados);
}

void handleLimpiar() {
  datosGuardados =
    "Punto,Distancia(mm),Inclinacion(deg),Alabeo(deg),Acimut(deg),Altitud(m),"
    "TempMPU(C),TempBMP(C),Presion(hPa),DistSueloCalibrada(mm)\n";
  server.sendHeader("Location", "/");
  server.send(303);
}

void handleJSON() {
  String json = "{";
  json += "\"distancia\":" + String(distance) + ",";
  json += "\"inclinacion\":" + String(roll, 1) + ",";
  json += "\"alabeo\":" + String(pitch, 1) + ",";
  json += "\"acimut\":" + String(heading) + ",";
  json += "\"altitud\":" + String(altitude, 1) + ",";
  json += "\"tempmpu\":" + String(tempMPU, 1) + ",";
  json += "\"tempbmp\":" + String(tempBMP, 1) + ",";
  json += "\"presion\":" + String(presionBMP, 1) + ",";
  json += "\"distancia_suelo_calibrada\":" + String(distanciaSueloCalibrada);
  json += "}";
  server.send(200, "application/json", json);
}

// ------------------- SETUP -------------------
void setup() {
  Serial.begin(115200);
  Wire.begin(SDA_PIN, SCL_PIN);

  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println("OLED no encontrado!");
    for (;;);
  }
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 0);
  display.println("Inicializando");
  display.setTextSize(2);
  display.setCursor(0, 16);
  display.println("PayoMapeo");
  display.display();

  if (!tof.init()) { Serial.println("VL53L0X no encontrado!"); while (1); }
  tof.setTimeout(500);

  if (!mpu.begin(0x68)) { Serial.println("MPU6050 no encontrado!"); while (1); }
  mpu.setAccelerometerRange(MPU6050_RANGE_4_G);
  mpu.setGyroRange(MPU6050_RANGE_500_DEG);
  mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);

  compass.init();

  if (!bmp.begin(0x76)) { Serial.println("BMP280 no encontrado!"); while (1); }

  WiFi.begin(ssid, password);
  Serial.print("Conectando a WiFi...");
  while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print("."); }
  Serial.println("\nConectado a WiFi!");
  Serial.print("IP asignada: ");
  Serial.println(WiFi.localIP());

  server.on("/", handleRoot);
  server.on("/json", handleJSON);
  server.on("/calibrar", HTTP_POST, handleCalibrar);
  server.on("/guardar", HTTP_POST, handleGuardar);
  server.on("/download", handleDownload);
  server.on("/limpiar", HTTP_POST, handleLimpiar);

  server.begin();
  Serial.println("Servidor web iniciado");
}

// ------------------- LOOP -------------------
void loop() {
  distance = tof.readRangeSingleMillimeters();

  sensors_event_t a, g, temp;
  mpu.getEvent(&a, &g, &temp);
  roll  = -atan2(a.acceleration.y, a.acceleration.z) * 57.3; // MODIFICA AQUÍ SEGÚN HAYAS MONTADO TU MPU6050 PARA OBTENER VALORES POSITIVOS CUANDO SUBES EL TELESCOPIO. EL SIGNO MENOS ESTÁ INVIRTIENDO LA INCLINACIÓN, PUEDES QUITARLO
  pitch = atan(-a.acceleration.x /
               sqrt(a.acceleration.y * a.acceleration.y + a.acceleration.z * a.acceleration.z)) * 57.3;
  tempMPU = temp.temperature;

  compass.read();
  heading = (compass.getAzimuth() + 180) % 360;  // MODIFICA AQUÍ SEGÚN HAYAS MONTADO TU BRÚJULA, ESTA ESTÁ GIRADA 180 GRADOS

  altitude = bmp.readAltitude(1013.25);
  tempBMP = bmp.readTemperature();
  presionBMP = bmp.readPressure() / 100.0F;

  // --- OLED (sin cambios) ---
  display.clearDisplay();
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.println("Entra en:");
  display.println(WiFi.localIP());
  display.print("Dist: "); display.print(distance); display.println(" mm");
  display.print("Incl: "); display.print(roll, 1); display.println(" deg");
  display.print("Alab: "); display.print(pitch, 1); display.println(" deg");
  display.print("Acim: "); display.print(heading); display.println(" deg");
  display.print("Alt: "); display.print(altitude, 1); display.println(" m");
  display.display();

  server.handleClient();
  delay(300);
}
