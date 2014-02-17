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

function user_budget() {
  var budget_el = $('#user_budget');
  var budget = parseInt(budget_el.text());

  // check extra budget per voucher
  $('.budget_extra').each(function() {
    var el = $(this);
    if(el.prop('checked')) {
      budget += parseInt(el.data('budget'));
    }
  });

  // nolimit?
  if($('.budget_nolimit').prop('checked')) {
    budget += 800;
  }

  return budget;
}

function voucher_budget() {
}

function update_order_value() {
  // update total order value
  var sum_el = $('#order_total_sum');
  var sum_available_el = $('#sum_available');
  var total = calculate_order_total();
  sum_el.val(total);
  sum_el.text(total);
  sum_available_el.text(user_budget());

  // order over budget?
  sum_el.css('color', 'green');
  $('#order_button').prop('disabled', false);
  if( parseInt(sum_el.val())>user_budget() ) {
    sum_el.css('color', 'red');
    $('#order_button').prop('disabled', true);
  }
}

function calculate_order_total() {
  var total = 0;
  $('input[class*="qty"]').each(function() {
    var self = $(this);
    var cost = parseInt(self.data('cost')) * parseInt(self.val()||0);
    total += cost;
  });
  return total;
}

/* NOTE: sync dateFormat with str2dt/parse server-side */
function csv_daterange() {
  $("#from").datepicker({
    defaultDate: "-2m",
    changeMonth: true,
    numberOfMonths: 3,
    onClose: function( selectedDate ) {
      $("#to").datepicker( "option", "minDate", selectedDate );
    },
    dateFormat: 'dd-mm-yy'
  });
  $("#to").datepicker({
    defaultDate: "+1d",
    changeMonth: true,
    numberOfMonths: 3,
    onClose: function( selectedDate ) {
      $("#from").datepicker( "option", "maxDate", selectedDate );
    },
    dateFormat: 'dd-mm-yy'
  });
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

function del_order(id) {
    $.ajax({
      url: url('order-detail', {pk: id}),
      type: 'DELETE',
      success: function(result) {
        window.location.reload();
      }
    });
}

$(function() {
  $('input[class*="qty"]').keyup(function() {
    update_order_value();
  });
  csv_daterange();
  var today = new Date(),
    tomorrow = new Date(),
    past = new Date();
  tomorrow.setDate(today.getDate() + 1);
  past.setDate(today.getDate() - 30);
  $('#from').datepicker("setDate", past);
  $('#to').datepicker("setDate", tomorrow);

  $('.budget_extra, .budget_nolimit').on('click', function() {
    update_order_value();
  });

  $('.delete_order').on('click', function() {
    var el = $(this);
    del_order(el.closest('tr').data('pk'));
    el.closest('tr').hide();
  });
});
