package com.jobscamguard.mobile

import android.content.Context
import android.graphics.Color
import android.graphics.PixelFormat
import android.graphics.drawable.GradientDrawable
import android.os.Build
import android.view.Gravity
import android.view.LayoutInflater
import android.view.WindowManager
import android.widget.TextView
import org.json.JSONObject

/** 夸克式：在屏幕边缘弹出小卡片显示结论，不跳转全屏页。 */
object FloatingResult {
    private var wm: WindowManager? = null
    private var card: android.view.View? = null
    private var params: WindowManager.LayoutParams? = null

    fun show(context: Context, json: JSONObject) {
        dismiss(context)
        val appCtx = context.applicationContext
        wm = appCtx.getSystemService(Context.WINDOW_SERVICE) as WindowManager
        val type = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
        } else {
            @Suppress("DEPRECATION")
            WindowManager.LayoutParams.TYPE_PHONE
        }
        val view = LayoutInflater.from(appCtx).inflate(R.layout.float_result, null)
        val level = json.optString("risk_level", "低危")
        val display = json.optString("risk_level_display", level)
        val score = json.optInt("risk_score", 0)
        val badge = view.findViewById<TextView>(R.id.resultBadge)
        val badgeColor = when (level) {
            "高危" -> Color.parseColor("#F87171")
            "中危" -> Color.parseColor("#FBBF24")
            else -> Color.parseColor("#34D399")
        }
        val badgeBg = GradientDrawable().apply {
            cornerRadius = 8f
            setColor(badgeColor)
        }
        badge.background = badgeBg
        badge.text = display
        view.findViewById<TextView>(R.id.resultScore).text = "$score 分"
        view.findViewById<TextView>(R.id.resultHeadline).text =
            json.optString("headline", "检测完成")
        val actions = json.optJSONArray("actions")
        val tip = if (actions != null && actions.length() > 0) {
            actions.getString(0)
        } else {
            ""
        }
        view.findViewById<TextView>(R.id.resultAction).text = tip
        view.findViewById<TextView>(R.id.resultClose).setOnClickListener {
            dismiss(appCtx)
        }
        params = WindowManager.LayoutParams(
            WindowManager.LayoutParams.WRAP_CONTENT,
            WindowManager.LayoutParams.WRAP_CONTENT,
            type,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE,
            PixelFormat.TRANSLUCENT,
        ).apply {
            gravity = Gravity.TOP or Gravity.CENTER_HORIZONTAL
            y = 120
        }
        wm?.addView(view, params)
        card = view
    }

    fun dismiss(context: Context) {
        card?.let {
            try {
                wm?.removeView(it)
            } catch (_: Exception) {
            }
        }
        card = null
    }
}
