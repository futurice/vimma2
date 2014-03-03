function url(name, c) {
  return URLS_BASE.slice(0,-1) + dutils.urls.resolve(name, c);
}

function incrementValue(el, value){
  var el = $(el);
  var container_el = el.closest('.panel-body');
  var input_el = $('input[class*="qty"]', container_el);
  var curval = parseInt(input_el.val()||0);
  var newValue = (curval+value>0) ? (curval+value) : 0;
  input_el.val(newValue);
  input_el.text(newValue);

  update_order_value();

  return false;
}

function voucher_iama() {
  $('#iama').on('submit', function(e) {
    var iama = $('input[name=iama]').val();
    $.cookie('iama', iama);
    e.preventDefault();
    window.location.reload();
  });
  var has_iama = $.cookie('iama');
  if(has_iama) {
    $('#iama_section').show();
  }
  $('#clear_iama').on('click', function(e) {
    $.removeCookie('iama');
  });
}
