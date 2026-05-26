package com.jobscamguard.mobile

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Intent
import android.content.pm.ServiceInfo
import android.media.projection.MediaProjectionManager
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat

class CaptureForegroundService : Service() {
  override fun onBind(intent: Intent?): IBinder? = null

  override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
    val channelId = "capture"
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
      val ch = NotificationChannel(channelId, getString(R.string.channel_capture), NotificationManager.IMPORTANCE_LOW)
      getSystemService(NotificationManager::class.java).createNotificationChannel(ch)
    }
    val notification: Notification = NotificationCompat.Builder(this, channelId)
      .setContentTitle(getString(R.string.app_name))
      .setContentText("屏幕分析已就绪，可使用悬浮球框选")
      .setSmallIcon(R.drawable.ic_launcher)
      .setOngoing(true)
      .build()
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
      startForeground(1, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PROJECTION)
    } else {
      @Suppress("DEPRECATION")
      startForeground(1, notification)
    }

    val resultCode = intent?.getIntExtra(EXTRA_RESULT_CODE, -1) ?: -1
    val data = intent?.getParcelableExtra<Intent>(EXTRA_DATA)
    if (resultCode != -1 && data != null) {
      val mgr = getSystemService(MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
      val projection = mgr.getMediaProjection(resultCode, data)
      ScreenCaptureHolder.bindProjection(projection)
    }
    stopForeground(STOP_FOREGROUND_DETACH)
    stopSelf()
    return START_NOT_STICKY
  }

  companion object {
    const val EXTRA_RESULT_CODE = "result_code"
    const val EXTRA_DATA = "data"
  }
}
