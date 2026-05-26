package com.jobscamguard.mobile

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.media.projection.MediaProjectionManager
import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity

class CapturePermissionActivity : AppCompatActivity() {
  override fun onCreate(savedInstanceState: Bundle?) {
    super.onCreate(savedInstanceState)
    val mgr = getSystemService(Context.MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
    @Suppress("DEPRECATION")
    startActivityForResult(mgr.createScreenCaptureIntent(), REQ)
  }

  @Deprecated("Deprecated in Java")
  override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
    super.onActivityResult(requestCode, resultCode, data)
    if (requestCode == REQ && resultCode == Activity.RESULT_OK && data != null) {
      val mgr = getSystemService(Context.MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
      @Suppress("DEPRECATION")
      val projection = mgr.getMediaProjection(resultCode, data)
      ScreenCaptureHolder.bindProjection(projection)
      Toast.makeText(this, "屏幕录制已授权", Toast.LENGTH_SHORT).show()
    } else {
      Toast.makeText(this, "未授权录屏，无法框选识图", Toast.LENGTH_LONG).show()
    }
    finish()
  }

  companion object {
    private const val REQ = 9001
  }
}
