package com.jobscamguard.mobile

import android.content.Context

object Prefs {
    private const val NAME = "job_scam_guard"

    fun serverUrl(ctx: Context): String =
        ctx.getSharedPreferences(NAME, Context.MODE_PRIVATE)
            .getString("server_url", "") ?: ""

    fun apiKey(ctx: Context): String =
        ctx.getSharedPreferences(NAME, Context.MODE_PRIVATE)
            .getString("api_key", "") ?: ""

    fun save(ctx: Context, url: String, key: String) {
        ctx.getSharedPreferences(NAME, Context.MODE_PRIVATE).edit()
            .putString("server_url", url.trim().removeSuffix("/"))
            .putString("api_key", key.trim())
            .apply()
    }
}
