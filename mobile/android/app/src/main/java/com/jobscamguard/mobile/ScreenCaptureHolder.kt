package com.jobscamguard.mobile

import android.graphics.Bitmap
import android.graphics.PixelFormat
import android.hardware.display.DisplayManager
import android.hardware.display.VirtualDisplay
import android.media.ImageReader
import android.media.projection.MediaProjection
import android.os.Handler
import android.os.Looper
import android.util.DisplayMetrics
import android.view.WindowManager
import java.nio.ByteBuffer

object ScreenCaptureHolder {
    var mediaProjection: MediaProjection? = null
    private var virtualDisplay: VirtualDisplay? = null
    private var imageReader: ImageReader? = null

    fun bindProjection(projection: MediaProjection) {
        releaseDisplay()
        mediaProjection = projection
    }

    fun releaseDisplay() {
        virtualDisplay?.release()
        virtualDisplay = null
        imageReader?.close()
        imageReader = null
    }

    fun releaseAll() {
        releaseDisplay()
        mediaProjection?.stop()
        mediaProjection = null
    }

    fun captureRegion(context: android.content.Context, left: Int, top: Int, right: Int, bottom: Int): Bitmap? {
        val projection = mediaProjection ?: return null
        val wm = context.getSystemService(WindowManager::class.java)
        val metrics = DisplayMetrics()
        @Suppress("DEPRECATION")
        wm.defaultDisplay.getRealMetrics(metrics)
        val width = metrics.widthPixels
        val height = metrics.heightPixels
        if (width < 1 || height < 1) return null

        releaseDisplay()
        imageReader = ImageReader.newInstance(width, height, PixelFormat.RGBA_8888, 2)
        virtualDisplay = projection.createVirtualDisplay(
            "JobScamCapture",
            width,
            height,
            metrics.densityDpi,
            DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR,
            imageReader!!.surface,
            null,
            Handler(Looper.getMainLooper()),
        )
        Thread.sleep(180)
        val image = imageReader?.acquireLatestImage() ?: return null
        val plane = image.planes[0]
        val buffer: ByteBuffer = plane.buffer
        val pixelStride = plane.pixelStride
        val rowStride = plane.rowStride
        val rowPadding = rowStride - pixelStride * width
        val full = Bitmap.createBitmap(
            width + rowPadding / pixelStride,
            height,
            Bitmap.Config.ARGB_8888,
        )
        full.copyPixelsFromBuffer(buffer)
        image.close()
        val screen = Bitmap.createBitmap(full, 0, 0, width, height)
        if (!full.isRecycled) full.recycle()

        val l = left.coerceIn(0, width - 1)
        val t = top.coerceIn(0, height - 1)
        val r = right.coerceIn(l + 1, width)
        val b = bottom.coerceIn(t + 1, height)
        return Bitmap.createBitmap(screen, l, t, r - l, b - t)
    }
}
