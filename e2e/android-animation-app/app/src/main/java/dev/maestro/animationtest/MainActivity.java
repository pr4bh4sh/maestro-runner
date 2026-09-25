package dev.maestro.animationtest;

import android.app.Activity;
import android.os.Bundle;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.webkit.JavascriptInterface;
import android.widget.Button;

public class MainActivity extends Activity {

    // Draw on a 2D <canvas> from setInterval (not a CSS transform / rAF). CSS
    // transform animations get promoted to a GPU compositor layer that does not
    // repaint under headless software rendering (-gpu swiftshader_indirect
    // -no-window), making frames static and breaking the "animation never ends"
    // E2E test. Canvas 2D is CPU-rasterized into the WebView backing store, so
    // every tick changes the rendered pixels and the animation stays detectable.
    private static final String SPINNER_HTML =
            "<!doctype html>\n" +
            "<html><head><meta charset=\"utf-8\">\n" +
            "<style>\n" +
            "  html,body{margin:0;height:100%;overflow:hidden;background:#fff}\n" +
            "  canvas{display:block;width:100%;height:100%}\n" +
            "</style></head><body><canvas id=\"c\"></canvas><script>\n" +
            "var c=document.getElementById('c'),x=c.getContext('2d');\n" +
            "function resize(){c.width=innerWidth;c.height=innerHeight;}\n" +
            "resize();addEventListener('resize',resize);\n" +
            "var a=0,iv;\n" +
            "function draw(){\n" +
            "  a=(a+3)%360;\n" +
            "  var w=c.width,h=c.height,cx=w/2,cy=h/2,r=Math.min(w,h)*0.18;\n" +
            "  x.fillStyle='#fff';x.fillRect(0,0,w,h);\n" +
            "  x.save();x.translate(cx,cy);x.rotate(a*Math.PI/180);\n" +
            "  x.fillStyle='#3498db';x.fillRect(-r,-r/6,r*2,r/3);x.restore();\n" +
            "}\n" +
            "iv=setInterval(draw,16);draw();\n" +
            "function stopAnimation(){if(iv){clearInterval(iv);iv=null;}}\n" +
            "function startAnimation(){if(!iv){iv=setInterval(draw,16);}}\n" +
            "</script></body></html>";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        WebView webView = findViewById(R.id.webview);
        webView.setWebViewClient(new WebViewClient());
        webView.getSettings().setJavaScriptEnabled(true);
        webView.getSettings().setDomStorageEnabled(true);
        webView.setImportantForAccessibility(android.view.View.IMPORTANT_FOR_ACCESSIBILITY_YES);
        webView.setContentDescription("Animation WebView");
        webView.addJavascriptInterface(new Object() {
            @JavascriptInterface
            public void onJsLog(String msg) { /* no-op, for debugging */ }
        }, "Android");
        webView.loadDataWithBaseURL(null, SPINNER_HTML, "text/html", "utf-8", null);

        Button stopButton = findViewById(R.id.stopButton);
        stopButton.setOnClickListener(v -> webView.evaluateJavascript("stopAnimation();", null));

        Button startButton = findViewById(R.id.startButton);
        startButton.setOnClickListener(v -> webView.evaluateJavascript("startAnimation();", null));
    }
}
