package com.taptap.clicker

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.GestureDescription
import android.app.Activity
import android.content.Context
import android.content.Intent
import android.content.SharedPreferences
import android.graphics.Color
import android.graphics.Path
import android.graphics.PixelFormat
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.provider.Settings
import android.text.InputType
import android.view.Gravity
import android.view.MotionEvent
import android.view.View
import android.view.ViewGroup
import android.view.WindowManager
import android.view.accessibility.AccessibilityEvent
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.SeekBar
import android.widget.TextView
import android.widget.Toast

/* ---------------- 配色（Claude 风格：暖白、留白、一个橘色主色） ---------------- */
object Palette {
    val BG = Color.parseColor("#F5F4EE")
    val CARD = Color.parseColor("#FFFFFF")
    val TEXT = Color.parseColor("#2E2E2B")
    val SUB = Color.parseColor("#7A7A73")
    val ACCENT = Color.parseColor("#D97757")
    val STOP = Color.parseColor("#B5493A")
    val LINE = Color.parseColor("#E9E7DE")
    val OK = Color.parseColor("#3D7A5A")
}

private const val PREFS = "taptap"
private const val MIN_MS = 20

/* ============================== 主界面 ============================== */
class MainActivity : Activity() {

    private lateinit var accLine: TextView
    private lateinit var accBtn: Button
    private lateinit var ovLine: TextView
    private lateinit var ovBtn: Button
    private lateinit var intervalLabel: TextView
    private lateinit var intervalBar: SeekBar
    private lateinit var countEdit: EditText

    private fun dp(v: Int) = (v * resources.displayMetrics.density).toInt()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val prefs = getSharedPreferences(PREFS, Context.MODE_PRIVATE)

        val scroll = ScrollView(this).apply { setBackgroundColor(Palette.BG) }
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(24), dp(44), dp(24), dp(44))
        }
        scroll.addView(root)

        root.addView(TextView(this).apply {
            text = "轻点"
            setTextColor(Palette.TEXT)
            textSize = 30f
            typeface = Typeface.create("sans-serif", Typeface.BOLD)
        })
        root.addView(TextView(this).apply {
            text = "一个简单的自动连点器"
            setTextColor(Palette.SUB)
            textSize = 15f
            setPadding(0, dp(6), 0, dp(24))
        })

        /* --- 权限卡片 --- */
        val permCard = card()
        permCard.addView(sectionTitle("权限"))
        accLine = line("无障碍服务 · 未开启")
        permCard.addView(accLine)
        accBtn = smallButton("去开启") { startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS)) }
        permCard.addView(accBtn)
        permCard.addView(divider())
        ovLine = line("悬浮窗 · 未开启")
        permCard.addView(ovLine)
        ovBtn = smallButton("去开启") {
            startActivity(Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION, Uri.parse("package:$packageName")))
        }
        permCard.addView(ovBtn)
        root.addView(permCard)

        /* --- 设置卡片 --- */
        val setCard = card()
        setCard.addView(sectionTitle("设置"))
        intervalLabel = TextView(this).apply { setTextColor(Palette.TEXT); textSize = 15f }
        setCard.addView(intervalLabel)
        intervalBar = SeekBar(this).apply {
            max = 1000
            progress = prefs.getInt("interval", 100).coerceIn(MIN_MS, MIN_MS + 1000) - MIN_MS
        }
        setCard.addView(intervalBar)
        updateIntervalLabel()
        intervalBar.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(s: SeekBar?, p: Int, u: Boolean) = updateIntervalLabel()
            override fun onStartTrackingTouch(s: SeekBar?) {}
            override fun onStopTrackingTouch(s: SeekBar?) {}
        })
        setCard.addView(divider())
        setCard.addView(TextView(this).apply {
            text = "点击次数（0 = 一直点）"
            setTextColor(Palette.TEXT); textSize = 15f
            setPadding(0, dp(2), 0, dp(6))
        })
        countEdit = EditText(this).apply {
            inputType = InputType.TYPE_CLASS_NUMBER
            setText(prefs.getInt("count", 0).toString())
            setTextColor(Palette.TEXT)
        }
        setCard.addView(countEdit)
        root.addView(setCard)

        /* --- 主按钮 --- */
        val start = TextView(this).apply {
            text = "开启悬浮窗"
            setTextColor(Color.WHITE)
            textSize = 17f
            gravity = Gravity.CENTER
            typeface = Typeface.DEFAULT_BOLD
            setPadding(0, dp(16), 0, dp(16))
            background = round(Palette.ACCENT, dp(16))
            setOnClickListener { launchOverlay(prefs) }
        }
        root.addView(start, LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT
        ).apply { topMargin = dp(28) })

        root.addView(TextView(this).apply {
            text = "开启后，拖动屏幕上的小圆点到你要点的位置，再按面板上的「开始」。"
            setTextColor(Palette.SUB); textSize = 13f
            setPadding(dp(2), dp(16), dp(2), 0)
        })

        setContentView(scroll)
    }

    private fun updateIntervalLabel() {
        intervalLabel.text = "点击间隔：${intervalBar.progress + MIN_MS} 毫秒"
    }

    override fun onResume() {
        super.onResume()
        val acc = accessibilityOn()
        setLine(accLine, "无障碍服务", acc); accBtn.visibility = if (acc) View.GONE else View.VISIBLE
        val ov = Settings.canDrawOverlays(this)
        setLine(ovLine, "悬浮窗", ov); ovBtn.visibility = if (ov) View.GONE else View.VISIBLE
    }

    private fun launchOverlay(prefs: SharedPreferences) {
        if (!accessibilityOn()) { toast("请先开启无障碍服务"); return }
        if (!Settings.canDrawOverlays(this)) { toast("请先开启悬浮窗权限"); return }
        prefs.edit()
            .putInt("interval", intervalBar.progress + MIN_MS)
            .putInt("count", countEdit.text.toString().toIntOrNull() ?: 0)
            .apply()
        val svc = ClickAccessibilityService.instance
        if (svc == null) { toast("无障碍服务未连接，请把开关关掉再打开一次"); return }
        svc.showOverlay()
        toast("悬浮窗已开启")
        moveTaskToBack(true)
    }

    private fun accessibilityOn(): Boolean {
        val target = "$packageName/$packageName.ClickAccessibilityService"
        val on = Settings.Secure.getString(contentResolver, Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES) ?: return false
        return on.split(':').any { it.equals(target, true) }
    }

    /* ---- 小工具：用代码搭出干净的卡片和控件 ---- */
    private fun card(): LinearLayout = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        background = round(Palette.CARD, dp(20))
        setPadding(dp(20), dp(18), dp(20), dp(18))
        layoutParams = LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT
        ).apply { topMargin = dp(16) }
    }

    private fun sectionTitle(t: String) = TextView(this).apply {
        text = t; setTextColor(Palette.SUB); textSize = 13f
        typeface = Typeface.DEFAULT_BOLD
        setPadding(0, 0, 0, dp(12))
    }

    private fun line(t: String) = TextView(this).apply {
        text = t; setTextColor(Palette.TEXT); textSize = 16f
        setPadding(0, dp(4), 0, dp(8))
    }

    private fun setLine(tv: TextView, name: String, on: Boolean) {
        tv.text = "$name · ${if (on) "已开启" else "未开启"}"
        tv.setTextColor(if (on) Palette.OK else Palette.TEXT)
    }

    private fun smallButton(t: String, onClick: () -> Unit) = Button(this).apply {
        text = t; setTextColor(Color.WHITE); textSize = 14f
        setAllCaps(false)
        background = round(Palette.ACCENT, dp(12))
        stateListAnimator = null
        setPadding(dp(20), dp(8), dp(20), dp(8))
        layoutParams = LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT
        )
        setOnClickListener { onClick() }
    }

    private fun divider() = View(this).apply {
        setBackgroundColor(Palette.LINE)
        layoutParams = LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(1))
            .apply { topMargin = dp(12); bottomMargin = dp(12) }
    }

    private fun round(color: Int, radius: Int) = GradientDrawable().apply {
        setColor(color); cornerRadius = radius.toFloat()
    }

    private fun toast(m: String) = Toast.makeText(this, m, Toast.LENGTH_SHORT).show()
}

/* ==================== 无障碍点击服务（负责真正点屏幕 + 悬浮窗） ==================== */
class ClickAccessibilityService : AccessibilityService() {

    companion object { var instance: ClickAccessibilityService? = null }

    private var wm: WindowManager? = null
    private var dot: View? = null
    private var dotParams: WindowManager.LayoutParams? = null
    private var panel: View? = null

    private val handler = Handler(Looper.getMainLooper())
    private var clicking = false
    private var limited = false
    private var remaining = 0
    private var intervalMs = 100L

    override fun onServiceConnected() {
        instance = this
        wm = getSystemService(Context.WINDOW_SERVICE) as WindowManager
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {}
    override fun onInterrupt() {}

    override fun onDestroy() {
        super.onDestroy()
        hideOverlay()
        instance = null
    }

    private fun dp(v: Int) = (v * resources.displayMetrics.density).toInt()

    private fun overlayType(): Int =
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O)
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
        else
            @Suppress("DEPRECATION") WindowManager.LayoutParams.TYPE_PHONE

    fun showOverlay() {
        val manager = wm ?: return
        if (dot != null) return
        val size = dp(46)

        // 可拖动的目标圆点
        val d = View(this).apply {
            background = GradientDrawable().apply {
                shape = GradientDrawable.OVAL
                setColor(0x66D97757)
                setStroke(dp(2), 0xFFD97757.toInt())
            }
        }
        val dPar = params(size, size, dp(140), dp(320))
        d.setOnTouchListener(Drag(dPar) { manager.updateViewLayout(d, dPar) })
        manager.addView(d, dPar)
        dot = d; dotParams = dPar

        // 开始 / 停止 面板（固定在左上角）
        val startStop = TextView(this).apply {
            text = "开始"; setTextColor(Color.WHITE); textSize = 15f
            typeface = Typeface.DEFAULT_BOLD; gravity = Gravity.CENTER
            setPadding(dp(22), dp(10), dp(22), dp(10))
            background = GradientDrawable().apply { setColor(0xFFD97757.toInt()); cornerRadius = dp(20).toFloat() }
        }
        val close = TextView(this).apply {
            text = "×"; setTextColor(0xFF7A7A73.toInt()); textSize = 20f
            gravity = Gravity.CENTER
            setPadding(dp(14), dp(4), dp(14), dp(8))
            setOnClickListener { hideOverlay() }
        }
        startStop.setOnClickListener {
            val bg = startStop.background as GradientDrawable
            if (clicking) { stopClicking(); startStop.text = "开始"; bg.setColor(0xFFD97757.toInt()) }
            else { startClicking(); startStop.text = "停止"; bg.setColor(0xFFB5493A.toInt()) }
        }
        val bar = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(dp(8), dp(6), dp(8), dp(6))
            background = GradientDrawable().apply {
                setColor(0xFFFFFFFF.toInt()); cornerRadius = dp(26).toFloat()
                setStroke(dp(1), 0xFFE9E7DE.toInt())
            }
            addView(startStop); addView(close)
        }
        val pPar = params(
            WindowManager.LayoutParams.WRAP_CONTENT,
            WindowManager.LayoutParams.WRAP_CONTENT, dp(20), dp(64)
        )
        manager.addView(bar, pPar)
        panel = bar
    }

    fun hideOverlay() {
        stopClicking()
        dot?.let { v -> runCatching { wm?.removeView(v) } }
        panel?.let { v -> runCatching { wm?.removeView(v) } }
        dot = null; panel = null; dotParams = null
    }

    private fun startClicking() {
        val prefs = getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        intervalMs = prefs.getInt("interval", 100).toLong().coerceAtLeast(MIN_MS.toLong())
        val c = prefs.getInt("count", 0)
        limited = c > 0; remaining = c
        dotParams?.let {
            it.flags = it.flags or WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE
            runCatching { wm?.updateViewLayout(dot, it) }
        }
        clicking = true
        handler.post(ticker)
    }

    private fun stopClicking() {
        clicking = false
        handler.removeCallbacks(ticker)
        dotParams?.let {
            it.flags = it.flags and WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE.inv()
            runCatching { wm?.updateViewLayout(dot, it) }
        }
    }

    private val ticker = object : Runnable {
        override fun run() {
            if (!clicking) return
            val d = dot ?: return
            val loc = IntArray(2)
            d.getLocationOnScreen(loc)
            tap((loc[0] + d.width / 2).toFloat(), (loc[1] + d.height / 2).toFloat())
            if (limited) {
                remaining--
                if (remaining <= 0) { stopClicking(); return }
            }
            handler.postDelayed(this, intervalMs)
        }
    }

    private fun tap(x: Float, y: Float) {
        val path = Path().apply { moveTo(x, y) }
        val stroke = GestureDescription.StrokeDescription(path, 0L, 20L)
        dispatchGesture(GestureDescription.Builder().addStroke(stroke).build(), null, null)
    }

    private fun params(w: Int, h: Int, x: Int, y: Int) = WindowManager.LayoutParams(
        w, h, overlayType(),
        WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or
            WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS,
        PixelFormat.TRANSLUCENT
    ).apply { gravity = Gravity.TOP or Gravity.START; this.x = x; this.y = y }

    private inner class Drag(
        val p: WindowManager.LayoutParams,
        val onMove: () -> Unit
    ) : View.OnTouchListener {
        private var ox = 0; private var oy = 0
        private var dx = 0f; private var dy = 0f
        override fun onTouch(v: View?, e: MotionEvent): Boolean {
            when (e.action) {
                MotionEvent.ACTION_DOWN -> { ox = p.x; oy = p.y; dx = e.rawX; dy = e.rawY; return true }
                MotionEvent.ACTION_MOVE -> {
                    p.x = ox + (e.rawX - dx).toInt()
                    p.y = oy + (e.rawY - dy).toInt()
                    onMove(); return true
                }
            }
            return false
        }
    }
}
