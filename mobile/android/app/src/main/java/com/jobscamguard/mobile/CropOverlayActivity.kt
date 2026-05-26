package com.jobscamguard.mobile

import android.content.Intent
import android.app.ProgressDialog
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Rect
import android.os.Bundle
import android.view.MotionEvent
import android.view.View
import android.widget.FrameLayout
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import kotlin.concurrent.thread

class CropOverlayActivity : AppCompatActivity() {
  private var startX = 0f
  private var startY = 0f
  private val sel = Rect()
  private lateinit var cropView: CropView

  override fun onCreate(savedInstanceState: Bundle?) {
    super.onCreate(savedInstanceState)
    val root = FrameLayout(this)
    cropView = CropView(this)
    root.addView(cropView, FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.MATCH_PARENT)
    val hint = TextView(this).apply {
      text = getString(R.string.crop_hint)
      setTextColor(Color.WHITE)
      textSize = 16f
      setPadding(32, 120, 32, 32)
    }
    root.addView(hint)
    setContentView(root)
  }

  inner class CropView(ctx: android.content.Context) : View(ctx) {
    private val dim = Paint().apply { color = Color.parseColor("#99000000") }
    private val fill = Paint().apply { color = Color.parseColor("#664D8DFF") }
    private val stroke = Paint().apply {
      color = Color.parseColor("#FF4D8DFF")
      style = Paint.Style.STROKE
      strokeWidth = 4f
    }

    override fun onDraw(canvas: Canvas) {
      super.onDraw(canvas)
      canvas.drawRect(0f, 0f, width.toFloat(), height.toFloat(), dim)
      if (!sel.isEmpty) {
        canvas.drawRect(sel, fill)
        canvas.drawRect(sel, stroke)
      }
    }

    override fun onTouchEvent(event: MotionEvent): Boolean {
      when (event.action) {
        MotionEvent.ACTION_DOWN -> {
          startX = event.x
          startY = event.y
          sel.set(startX.toInt(), startY.toInt(), startX.toInt(), startY.toInt())
          invalidate()
        }
        MotionEvent.ACTION_MOVE -> {
          sel.set(
            minOf(startX, event.x).toInt(),
            minOf(startY, event.y).toInt(),
            maxOf(startX, event.x).toInt(),
            maxOf(startY, event.y).toInt(),
          )
          invalidate()
        }
        MotionEvent.ACTION_UP -> {
          if (sel.width() < 48 || sel.height() < 48) {
            Toast.makeText(ctx, "选区太小，请重新框选", Toast.LENGTH_SHORT).show()
            return true
          }
          runCaptureAndUpload()
        }
      }
      return true
    }
  }

  private fun runCaptureAndUpload() {
    val dialog = ProgressDialog.show(this, null, "截图识别中…", true, false)
    thread {
      try {
        val bmp = ScreenCaptureHolder.captureRegion(
          this,
          sel.left,
          sel.top,
          sel.right,
          sel.bottom,
        ) ?: throw IllegalStateException("截屏失败，请重新授权录屏")
        val json = ApiClient.analyzeImage(
          Prefs.serverUrl(this),
          Prefs.apiKey(this),
          bmp,
          useAi = false,
          provider = "none",
        )
        bmp.recycle()
        runOnUiThread {
          dialog.dismiss()
          FloatingResult.show(this@CropOverlayActivity, json)
          finish()
        }
      } catch (e: Exception) {
        runOnUiThread {
          dialog.dismiss()
          Toast.makeText(this, "失败: ${e.message}", Toast.LENGTH_LONG).show()
          finish()
        }
      }
    }
  }
}
