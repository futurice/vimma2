(function(document) {
  'use strict';
  var app = document.querySelector('#app');
  app.addEventListener('dom-change', function() {
  });

  window.addEventListener('WebComponentsReady', function() {
  });

  app.onMenuSelect = function() {
    var drawerPanel = document.querySelector('#paperDrawerPanel');
    if (drawerPanel.narrow) {
      drawerPanel.closeDrawer();
    }
  };

})(document);
