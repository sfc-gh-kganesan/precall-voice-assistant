hushly.bombora = true;
hushly.variables = [{"name":"UTM Content","code":"utm_content_c","dataType":"String","sourceType":"Function","source":"function getUtmContent() {\r\n   var url = window.location.href.includes('?') ? window.location.href+'-hushly' : window.location.href + '?utm_cta=hushly';\r\n   return url.substring(510, 765);\r\n}","systemDefined":false},{"name":"UTM Term","code":"utm_term_c","dataType":"String","sourceType":"Function","source":"function getUtmTerm() {\r\n   var url = window.location.href.includes('?') ? window.location.href+'-hushly' : window.location.href + '?utm_cta=hushly';\r\n   return url.substring(255, 510);\r\n}","systemDefined":false},{"name":"UTM Ad Group","code":"ad_group_c","dataType":"String","sourceType":"Function","source":"function getUtmAdGroup() {\r\n   var url = window.location.href.includes('?') ? window.location.href+'-hushly' : window.location.href + '?utm_cta=hushly';\r\n   return url.substring(0, 255);\r\n}","systemDefined":false},{"name":"utm_cta_equals_hushly","code":"utm_cta_equals_hushly_c","dataType":"String","sourceType":"Function","source":"function getCustomUrl() {\r\n    //var urlParams = new URLSearchParams(window.location.search);\r\n    //urlParams.set('utm_CTA', 'Hushly');\r\n    //return window.location + urlParams;\r\n   var url = new URL(window.location.href);\r\n   url.searchParams.set('utm_CTA', 'Hushly');\r\n   return url.toString()\r\n}","systemDefined":false}];
!function() {
    var hly_config = {
        cdn: "https://app.hushly.com/",
        css: "https://tag.hushly.com/exp/widget-9b581f37c15d0fd98691e1e6ddf2477e.css",
        api: "https://app.hushly.com/",
        coreApi: "https://core-api.hushly.com/",
        eventApi: "https://events.hushly.com/",
        eventApiVersion: "v2",
        sessionTimeout: "30",
        timeTrackerIdleTimeout: "60",
        timeTrackerHeartbeatInterval: "15",
        scripts: {
            libraries: [
                "https://tag.hushly.com/exp/widget-lib-1-efb34ff65b65b2cb0c9b4603b488405f.js",
                "https://tag.hushly.com/exp/widget-lib-2-71e90bdbaf8e69fb602dc214e6869f8e.js"
            ],
            core: "https://tag.hushly.com/exp/widget-core-839d5538eb9eb6e2532b060799d54934.js",
        }
    };
    for(var prop in hly_config) hushly[prop] = hly_config[prop];

    var scriptTag = document.createElement("script");
    scriptTag.type = "text/javascript"; 
    scriptTag.async = true; 
    scriptTag.src = window._hlyc || "https://tag.hushly.com/exp/widget-f80cafb887577df523af721b08e97314.js";
    (document.getElementsByTagName("head")[0] 
                    || document.documentElement).appendChild(scriptTag);
}();//ccm informer
(function(f,i,c){var a=decodeURIComponent,e="",l="",o="||",g=";;",h="split",b="length",j="indexOf",k=0,n="localStorage",m="_ccmdt";f[c]=f[c]||{};function d(q){var p;if(f[n]){return f[n][q]||""}else{p=i.cookie.match(q+"=([^;]*)");return(p&&p[1])||""}}f[c].us={};e=a(d(m))[h](o);k=e[b];if(k>0){while(k--){l=e[k][h]("=");if(l[b]>1){if(l[1][j](g)>-1){f[c].us[l[0]]=l[1][h](g);f[c].us[l[0]].pop()}else{f[c].us[l[0]]=l[1]}}}}})(window,document,"_ml");

//ccm tag
function loadBomboraTag() {
    _ml = window._ml || {};
    _ml.eid = '69480';
    _ml.informer = {
        callbackAlways: true,
        callback: function(){
            if (window._hly_bombora_us) {
                _ml.us = window._hly_bombora_us;
            }
            hushly("event", "hly-bombora-informer-ready");
        },
        enable: true
    };
    var s = document.getElementsByTagName('script')[0], cd = new Date(), mltag = document.createElement('script');
    mltag.type = 'text/javascript'; mltag.async = true;
    mltag.src = 'https://ml314.com/tag.aspx?' + cd.getDate() + cd.getMonth() + cd.getFullYear();
    s.parentNode.insertBefore(mltag, s);
};

(function() {
    if (document.readyState === 'ready' || document.readyState === 'complete') {
        loadBomboraTag();
    } else {
        window.addEventListener('load', loadBomboraTag);
    }
})();
