package com.ruanxiaomi.reader;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.view.ViewGroup;
import android.webkit.WebBackForwardList;
import android.webkit.WebChromeClient;
import android.webkit.WebHistoryItem;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

public final class MainActivity extends Activity {
    private WebView webView;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        DailyIconManager.applyForToday(this);
        IconRotationScheduler.ensureScheduled(this);

        webView = new WebView(this);
        webView.setBackgroundColor(Color.rgb(245, 241, 232));
        webView.setLayoutParams(new ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT
        ));

        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setMediaPlaybackRequiresUserGesture(false);
        settings.setLoadWithOverviewMode(false);
        settings.setUseWideViewPort(true);
        settings.setBuiltInZoomControls(false);
        settings.setDisplayZoomControls(false);

        // Keep the normal WebView cache for article/audio offline use.
        // Only the top-level reader HTML is cache-busted on app launch below.
        settings.setCacheMode(WebSettings.LOAD_DEFAULT);

        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(false);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);

        webView.setWebChromeClient(new WebChromeClient());
        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri uri = request.getUrl();
                String host = uri.getHost();
                if (host != null && host.equalsIgnoreCase("dannhitruong852-jpg.github.io")) {
                    return false;
                }
                try {
                    startActivity(new Intent(Intent.ACTION_VIEW, uri));
                    return true;
                } catch (Exception ignored) {
                    return false;
                }
            }
        });

        setContentView(webView);

        String fragment = null;
        if (savedInstanceState != null) {
            WebBackForwardList restored = webView.restoreState(savedInstanceState);
            if (restored != null) {
                WebHistoryItem current = restored.getCurrentItem();
                if (current != null) {
                    Uri restoredUri = Uri.parse(current.getUrl());
                    if (isReaderUri(restoredUri)) {
                        fragment = restoredUri.getFragment();
                    }
                }
            }
        }

        // Always fetch a fresh copy of the outer HTML on app creation.
        // The changing query parameter bypasses stale WebView/GitHub Pages HTML cache,
        // while versioned JS/CSS, article JSON and audio remain cacheable/offline.
        webView.loadUrl(freshReaderUrl(fragment));
    }

    private boolean isReaderUri(Uri uri) {
        String host = uri.getHost();
        String path = uri.getPath();
        return host != null
                && host.equalsIgnoreCase("dannhitruong852-jpg.github.io")
                && path != null
                && path.startsWith("/taptap/kaoyan-reader-v1/");
    }

    private String freshReaderUrl(String fragment) {
        Uri.Builder builder = Uri.parse(BuildConfig.READER_URL)
                .buildUpon()
                .appendQueryParameter("_app_refresh", String.valueOf(System.currentTimeMillis()));
        if (fragment != null && !fragment.isEmpty()) {
            builder.fragment(fragment);
        }
        return builder.build().toString();
    }

    @Override
    protected void onSaveInstanceState(Bundle outState) {
        webView.saveState(outState);
        super.onSaveInstanceState(outState);
    }

    @Override
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) {
            webView.goBack();
        } else {
            super.onBackPressed();
        }
    }

    @Override
    protected void onDestroy() {
        if (webView != null) {
            ViewGroup parent = (ViewGroup) webView.getParent();
            if (parent != null) parent.removeView(webView);
            webView.removeAllViews();
            webView.destroy();
            webView = null;
        }
        super.onDestroy();
    }
}
