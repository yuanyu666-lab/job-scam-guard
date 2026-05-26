package com.jobscamguard.mobile

import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat

class MainActivity : AppCompatActivity() {
  override fun onCreate(savedInstanceState: Bundle?) {
    super.onCreate(savedInstanceState)
    setContentView(R.layout.activity_main)
    val serverUrl = findViewById<EditText>(R.id.serverUrl)
    val apiKey = findViewById<EditText>(R.id.apiKey)
    val status = findViewById<TextView>(R.id.statusText)
    serverUrl.setText(Prefs.serverUrl(this))
    apiKey.setText(Prefs.apiKey(this))
    updateStatus(status)

  findViewById<Button>(R.id.btnOverlay).setOnClickListener {
      if (!Settings.canDrawOverlays(this)) {
        val intent = Intent(
          Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
          Uri.parse("package:$packageName"),
        )
        startActivity(intent)
        Toast.makeText(this, "请允许「显示在其他应用上层」", Toast.LENGTH_LONG).show()
      } else {
        Toast.makeText(this, "悬浮窗权限已开启", Toast.LENGTH_SHORT).show()
      }
    }

    findViewById<Button>(R.id.btnCapture).setOnClickListener {
      startActivity(Intent(this, CapturePermissionActivity::class.java))
    }

    findViewById<Button>(R.id.btnStartBubble).setOnClickListener {
      if (Prefs.serverUrl(this).isBlank()) {
        Toast.makeText(this, "请先填写 HTTPS 服务器地址", Toast.LENGTH_LONG).show()
        return
      }
      Prefs.save(this, serverUrl.text.toString(), apiKey.text.toString())
      if (!Settings.canDrawOverlays(this)) {
        Toast.makeText(this, "请先授权悬浮窗", Toast.LENGTH_LONG).show()
        return
      }
      if (ScreenCaptureHolder.mediaProjection == null) {
        Toast.makeText(this, "请先授权屏幕录制", Toast.LENGTH_LONG).show()
        return
      }
      if (Build.VERSION.SDK_INT >= 33) {
        ActivityCompat.requestPermissions(
          this,
          arrayOf(android.Manifest.permission.POST_NOTIFICATIONS),
          100,
        )
      }
      ContextCompat.startForegroundService(
        this,
        Intent(this, FloatBubbleService::class.java),
      )
      Toast.makeText(this, "悬浮球已启动，可切到其他 App", Toast.LENGTH_LONG).show()
      updateStatus(status)
    }

    findViewById<Button>(R.id.btnStopBubble).setOnClickListener {
      stopService(Intent(this, FloatBubbleService::class.java))
      Toast.makeText(this, "已停止悬浮球", Toast.LENGTH_SHORT).show()
      updateStatus(status)
    }
  }

  override fun onResume() {
    super.onResume()
    findViewById<TextView>(R.id.statusText)?.let { updateStatus(it) }
  }

  private fun updateStatus(tv: TextView) {
    val overlay = Settings.canDrawOverlays(this)
    val cap = ScreenCaptureHolder.mediaProjection != null
    tv.text = buildString {
      append("悬浮窗：").append(if (overlay) "已授权" else "未授权").append('\n')
      append("录屏：").append(if (cap) "已授权" else "未授权").append('\n')
      append("服务器：").append(Prefs.serverUrl(this).ifBlank { "未配置" })
    }
  }
}
