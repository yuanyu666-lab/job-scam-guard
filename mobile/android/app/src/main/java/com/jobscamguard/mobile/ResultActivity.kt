package com.jobscamguard.mobile

import android.os.Bundle
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import org.json.JSONObject

class ResultActivity : AppCompatActivity() {
  override fun onCreate(savedInstanceState: Bundle?) {
    super.onCreate(savedInstanceState)
    val tv = TextView(this).apply {
      setTextColor(0xFFEEF2F7.toInt())
      textSize = 15f
      setPadding(48, 48, 48, 48)
    }
    setContentView(tv)
    val raw = intent.getStringExtra(EXTRA_JSON) ?: "{}"
    val j = JSONObject(raw)
    val level = j.optString("risk_level_display", j.optString("risk_level", "?"))
    val score = j.optInt("risk_score", 0)
    val headline = j.optString("headline", "")
    val actions = j.optJSONArray("actions")
    val sb = StringBuilder()
    sb.append("【").append(level).append("】 ").append(score).append(" 分\n\n")
    sb.append(headline).append("\n\n")
    if (actions != null) {
      for (i in 0 until actions.length()) {
        sb.append("• ").append(actions.getString(i)).append('\n')
      }
    }
    val preview = j.optString("ocr_text_preview", "")
    if (preview.isNotBlank()) {
      sb.append("\n—— OCR 摘要 ——\n").append(preview.take(400))
    }
    tv.text = sb.toString()
  }

  companion object {
    const val EXTRA_JSON = "result_json"
  }
}
