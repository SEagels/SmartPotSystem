/**
 * wifi_manager.h — WiFi 连接管理
 */

#ifndef WIFI_MANAGER_H
#define WIFI_MANAGER_H

#include <WiFi.h>

void wifi_init();
void wifi_loop();
bool wifi_is_connected();
int  wifi_get_rssi();
const char* wifi_get_ip();

#endif
