// harwood0 camera: joins WiFi and serves JPEG frames from the OV2640 over HTTP.
//
//   http://harwood0-<name>.local/          status as JSON
//   http://harwood0-<name>.local/capture   one JPEG
//   http://harwood0-<name>.local:81/stream MJPEG (multipart/x-mixed-replace), one client at a time
//
// The stream has its own server because a stream holds its server's only task for as long
// as it runs. Each part carries Content-Length, so readers can split frames without scanning
// for JPEG markers.

#include <Arduino.h>
#include <ESPmDNS.h>
#include <WiFi.h>
#include <esp_camera.h>
#include <esp_http_server.h>

#if __has_include("secrets.h")
#include "secrets.h"
#else
#error "Missing include/secrets.h: copy include/secrets.example.h and set WiFi credentials"
#endif

#ifndef CAMERA_NAME
#define CAMERA_NAME "camera"
#endif

namespace {

constexpr char kHostname[] = "harwood0-" CAMERA_NAME;
constexpr char kFirmwareVersion[] = "0.1.0";
constexpr uint16_t kStreamPort = 81;

// 640x480 at JPEG quality 12 (0-63, lower is better) runs at about 20 fps on a good link.
constexpr framesize_t kFrameSize = FRAMESIZE_VGA;
constexpr int kJpegQuality = 12;
// Set these if the image comes out upside down or mirrored for how the module is mounted.
constexpr bool kVFlip = false;
constexpr bool kHMirror = false;

// AI-Thinker ESP32-CAM pin map.
constexpr int kPinPwdn = 32;
constexpr int kPinXclk = 0;
constexpr int kPinSda = 26;
constexpr int kPinScl = 27;
constexpr int kPinData[] = {5, 18, 19, 21, 36, 39, 34, 35};  // D0-D7 (Y2-Y9)
constexpr int kPinVsync = 25;
constexpr int kPinHref = 23;
constexpr int kPinPclk = 22;
constexpr int kPinFlashLed = 4;

constexpr char kBoundary[] = "frame";
constexpr char kStreamContentType[] = "multipart/x-mixed-replace;boundary=frame";

uint32_t framesServed = 0;
bool streaming = false;

bool startCamera() {
  camera_config_t config = {};
  config.pin_pwdn = kPinPwdn;
  config.pin_reset = -1;
  config.pin_xclk = kPinXclk;
  config.pin_sccb_sda = kPinSda;
  config.pin_sccb_scl = kPinScl;
  config.pin_d0 = kPinData[0];
  config.pin_d1 = kPinData[1];
  config.pin_d2 = kPinData[2];
  config.pin_d3 = kPinData[3];
  config.pin_d4 = kPinData[4];
  config.pin_d5 = kPinData[5];
  config.pin_d6 = kPinData[6];
  config.pin_d7 = kPinData[7];
  config.pin_vsync = kPinVsync;
  config.pin_href = kPinHref;
  config.pin_pclk = kPinPclk;
  config.xclk_freq_hz = 20000000;
  config.ledc_timer = LEDC_TIMER_0;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size = kFrameSize;
  config.jpeg_quality = kJpegQuality;
  // Two buffers in PSRAM, always handing out the newest frame, so a slow reader sees fresh
  // frames rather than a backlog.
  config.fb_count = 2;
  config.fb_location = CAMERA_FB_IN_PSRAM;
  config.grab_mode = CAMERA_GRAB_LATEST;

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("camera init failed: 0x%x\n", err);
    return false;
  }
  sensor_t* sensor = esp_camera_sensor_get();
  sensor->set_vflip(sensor, kVFlip);
  sensor->set_hmirror(sensor, kHMirror);
  return true;
}

esp_err_t handleStatus(httpd_req_t* req) {
  char body[256];
  snprintf(body, sizeof(body),
           "{\"name\":\"%s\",\"firmware\":\"%s\",\"frame_size\":\"%dx%d\",\"rssi\":%d,"
           "\"uptime_ms\":%lu,\"streaming\":%s,\"frames_served\":%lu}",
           CAMERA_NAME, kFirmwareVersion, resolution[kFrameSize].width,
           resolution[kFrameSize].height, WiFi.RSSI(), millis(), streaming ? "true" : "false",
           framesServed);
  httpd_resp_set_type(req, "application/json");
  return httpd_resp_sendstr(req, body);
}

esp_err_t handleCapture(httpd_req_t* req) {
  camera_fb_t* fb = esp_camera_fb_get();
  if (!fb) {
    httpd_resp_send_500(req);
    return ESP_FAIL;
  }
  httpd_resp_set_type(req, "image/jpeg");
  esp_err_t err = httpd_resp_send(req, reinterpret_cast<const char*>(fb->buf), fb->len);
  esp_camera_fb_return(fb);
  return err;
}

esp_err_t handleStream(httpd_req_t* req) {
  httpd_resp_set_type(req, kStreamContentType);
  httpd_resp_set_hdr(req, "Cache-Control", "no-store");
  Serial.println("stream started");
  streaming = true;
  esp_err_t err = ESP_OK;
  char header[128];
  while (err == ESP_OK) {
    camera_fb_t* fb = esp_camera_fb_get();
    if (!fb) {
      Serial.println("frame capture failed");
      err = ESP_FAIL;
      break;
    }
    int n = snprintf(header, sizeof(header),
                     "--%s\r\nContent-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n",
                     kBoundary, fb->len);
    err = httpd_resp_send_chunk(req, header, n);
    if (err == ESP_OK)
      err = httpd_resp_send_chunk(req, reinterpret_cast<const char*>(fb->buf), fb->len);
    if (err == ESP_OK) err = httpd_resp_send_chunk(req, "\r\n", 2);
    esp_camera_fb_return(fb);
    if (err == ESP_OK) framesServed++;
  }
  streaming = false;
  Serial.println("stream ended");
  return err;
}

void startServers() {
  httpd_config_t config = HTTPD_DEFAULT_CONFIG();
  httpd_handle_t control = nullptr;
  if (httpd_start(&control, &config) == ESP_OK) {
    httpd_uri_t status = {"/", HTTP_GET, handleStatus, nullptr};
    httpd_uri_t capture = {"/capture", HTTP_GET, handleCapture, nullptr};
    httpd_register_uri_handler(control, &status);
    httpd_register_uri_handler(control, &capture);
  }

  config.server_port = kStreamPort;
  config.ctrl_port += 1;  // each server needs its own control socket
  httpd_handle_t stream = nullptr;
  if (httpd_start(&stream, &config) == ESP_OK) {
    httpd_uri_t streamUri = {"/stream", HTTP_GET, handleStream, nullptr};
    httpd_register_uri_handler(stream, &streamUri);
  }
}

// Every 10 s, so a dropped link shows up in the serial log.
void reportStatus() {
  static uint32_t lastMs = 0;
  if (millis() - lastMs < 10000) return;
  lastMs = millis();
  Serial.printf("wifi %s, rssi %d dBm, %s, %lu frames served\n",
                WiFi.status() == WL_CONNECTED ? "up" : "DOWN", WiFi.RSSI(),
                streaming ? "streaming" : "idle", framesServed);
}

}  // namespace

void setup() {
  Serial.begin(115200);
  Serial.printf("\nharwood0 camera %s %s\n", CAMERA_NAME, kFirmwareVersion);

  pinMode(kPinFlashLed, OUTPUT);
  digitalWrite(kPinFlashLed, LOW);

  if (!psramFound()) Serial.println("no PSRAM found; is this an AI-Thinker board?");
  if (!startCamera()) {
    Serial.println("check the camera's ribbon cable is seated; restarting in 5 s");
    delay(5000);
    ESP.restart();
  }

  WiFi.mode(WIFI_STA);
  WiFi.setHostname(kHostname);
  WiFi.setSleep(false);  // power saving adds tens of ms of latency to every frame
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("connecting to " WIFI_SSID);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.printf("\nconnected, rssi %d dBm\n", WiFi.RSSI());

  if (MDNS.begin(kHostname)) MDNS.addService("http", "tcp", 80);
  startServers();
  IPAddress ip = WiFi.localIP();
  Serial.printf("status  http://%s.local/  (http://%s/)\n", kHostname, ip.toString().c_str());
  Serial.printf("stream  http://%s.local:%u/stream\n", kHostname, kStreamPort);
}

void loop() {
  reportStatus();
  delay(100);
}
