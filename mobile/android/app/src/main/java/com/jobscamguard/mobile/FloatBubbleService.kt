package com.jobscamguard.mobile

import android.app.Service
import android.content.Intent
import android.graphics.PixelFormat
import android.os.Build
import android.os.IBinder
import android.util.DisplayMetrics
import android.view.Gravity
import android.view.LayoutInflater
import android.view.MotionEvent
import android.view.View
import android.view.WindowManager
import android.widget.Toast

/**
 * 夸克式小悬浮球：可拖动、松手贴左右边；点击开始框选识图。
 */
class FloatBubbleService : Service() {
  private var wm: WindowManager? = null
  private var bubble: View? = null
  private var params: WindowManager.LayoutParams? = null
  private var downX = 0f
  private var downY = 0f
  private var startX = 0
  private var startY = 0
  private var screenW = 1080

  override fun onBind(intent: Intent?): IBinder? = null

  override fun onCreate() {
    super.onCreate()
    wm = getSystemService(WINDOW_SERVICE) as WindowManager
    val metrics = DisplayMetrics()
    @Suppress("DEPRECATION")
    wm?.defaultDisplay?.getRealMetrics(metrics)
    screenW = metrics.widthPixels

    val type = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
      WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
    } else {
      @Suppress("DEPRECATION")
      WindowManager.LayoutParams.TYPE_PHONE
    }
    val view = LayoutInflater.from(this).inflate(R.layout.bubble, null)
    params = WindowManager.LayoutParams(
      WindowManager.LayoutParams.WRAP_CONTENT,
      WindowManager.LayoutParams.WRAP_CONTENT,
      type,
      WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE,
      PixelFormat.TRANSLUCENT,
    ).apply {
      gravity = Gravity.TOP or Gravity.START
      x = screenW - 46 - 24
      y = metrics.heightPixels / 3
    }
    view.setOnTouchListener { _, e ->
      when (e.action) {
        MotionEvent.ACTION_DOWN -> {
          downX = e.rawX
          downY = e.rawY
          startX = params!!.x
          startY = params!!.y
          true
        }
        MotionEvent.ACTION_MOVE -> {
          params!!.x = startX + (e.rawX - downX).toInt()
          params!!.y = startY + (e.rawY - downY).toInt()
          wm?.updateViewLayout(view, params)
          true
        }
        MotionEvent.ACTION_UP -> {
          val moved = kotlin.math.abs(e.rawX - downX) > 10 || kotlin.math.abs(e.rawY - downY) > 10
          if (!moved) {
            onBubbleClick()
          } else {
            snapToEdge(view)
          }
          true
        }
        else -> false
      }
    }
    wm?.addView(view, params)
    bubble = view
  }

  private fun snapToEdge(view: View) {
    val mid = screenW / 2
    params!!.x = if (params!!.x + 23 < mid) 8 else screenW - 46 - 16
    wm?.updateViewLayout(view, params)
  }

  private fun onBubbleClick() {
    if (ScreenCaptureHolder.mediaProjection == null) {
      Toast.makeText(this, "请先在 App 内授权屏幕录制", Toast.LENGTH_LONG).show()
      startActivity(
        Intent(this, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK),
      )
      return
    }
    FloatingResult.dismiss(this)
    startActivity(
      Intent(this, CropOverlayActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK),
    )
  }

  override fun onDestroy() {
    FloatingResult.dismiss(this)
    bubble?.let { wm?.removeView(it) }
    bubble = null
    super.onDestroy()
  }
}
