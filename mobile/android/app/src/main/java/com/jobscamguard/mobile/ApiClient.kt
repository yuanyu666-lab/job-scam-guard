package com.jobscamguard.mobile

import android.graphics.Bitmap
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.util.concurrent.TimeUnit

object ApiClient {
    private val client = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(120, TimeUnit.SECONDS)
        .writeTimeout(120, TimeUnit.SECONDS)
        .build()

    fun analyzeImage(
        baseUrl: String,
        apiKey: String,
        bitmap: Bitmap,
        useAi: Boolean = false,
        provider: String = "none",
    ): JSONObject {
        val q = buildString {
            append("?use_ai=").append(useAi)
            append("&provider=").append(provider)
        }
        val url = baseUrl.trim().removeSuffix("/") + "/api/analyze/image" + q
        val stream = ByteArrayOutputStream()
        bitmap.compress(Bitmap.CompressFormat.PNG, 92, stream)
        val body = MultipartBody.Builder()
            .setType(MultipartBody.FORM)
            .addFormDataPart(
                "file",
                "crop.png",
                stream.toByteArray().toRequestBody("image/png".toMediaType()),
            )
            .build()
        val builder = Request.Builder().url(url).post(body)
        if (apiKey.isNotBlank()) {
            builder.addHeader("X-API-Key", apiKey)
        }
        val resp = client.newCall(builder.build()).execute()
        val text = resp.body?.string() ?: "{}"
        if (!resp.isSuccessful) {
            val detail = try {
                JSONObject(text).optString("detail", text)
            } catch (_: Exception) {
                text
            }
            throw IllegalStateException(detail.ifBlank { "HTTP ${resp.code}" })
        }
        return JSONObject(text)
    }
}
