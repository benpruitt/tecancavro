
$(document).ready(function() {

+$( "#extract_btn" ).click(function( event ) {
    var volume = $( "#extract_volume").val();
    var port = $("#port_number").val();
    var serport = $( "#serial_port").val() || '';
    var rate = $("#rate_box").val();
    
    if ( volume > 0 && volume <= 5000) {
        $( "#debugfield" ).text( "Valid extract command..." ).show();
        $.get('extract',
              {'volume': volume,
               'port': port,
               'serial_port': serport,
               'exec': 1,
               'rate': rate
                }
            );
        
    } else {
        $( "#debugfield" ).text( "Not valid extract command!" ).show().fadeOut( 1000 );
    }
    event.preventDefault();
});

$('#rate1').selectize();

$( "#resetbutton" ).click(function( event ) {
  var serport = $( "#serial_port").val() || '';
  $.get('reset',
              {'serial_port': serport
              }
            );
  event.preventDefault();
});
$( "#pausebutton" ).click(function( event ) {
  var serport = $( "#serial_port").val() || '';
  $.get('pause',
              {'serial_port': serport
              }
            );
  event.preventDefault();
});
$( "#resumebutton" ).click(function( event ) {
  var serport = $( "#serial_port").val() || '';
  $.get('resume',
              {'serial_port': serport
              }
            );
  event.preventDefault();
});

$( "#dispense_btn" ).click(function( event ) {
    var volume = $( "#dispense_volume").val();
    var port = $("#port_number").val();
    var serport = $( "#serial_port").val() || '';
    var rate = $("#rate_box").val();
    if ( volume > 0 && volume <= 5000) {
        $( "#debugfield" ).text( "Validated dispense command..." ).show();
        $.get('dispense',
              {'volume': volume,
               'port': port,
               'serial_port': serport,
               'exec': 1,
               'rate': rate
                }
            );
        
    } else {
        $( "#debugfield" ).text( "Not valid dispense command!" ).show().fadeOut( 1000 );
    }

    event.preventDefault();
});

$( "#submitProtocolAdv" ).click(function( event ) {

  var serport = $( "#serial_port").val() || '';
  var oTable = document.getElementById('protocolTable');
  var rowLength = oTable.rows.length;
  var fromports = [];
  var toports = [];
  var hours = [];
  var minutes = [];
  var seconds = [];
  var flowrates = [];
  var volumes = [];
  var cycles = [];
  var repeats = [];


  for (i = 1; i < rowLength; i++){
      var oCells = oTable.rows.item(i).cells;

       //gets amount of cells of current row
      var cellLength = oCells.length;

      str = oCells.item(3).innerHTML;

      var numberPattern = /\d+/g;
      var idnum = str.match( numberPattern )[1]

      var idstr = "from" + idnum;
      var inportId = document.getElementById(idstr);
      inport = inportId.options[inportId.selectedIndex].value;
      fromports[i-1] = inport;

      var idstr = "to" + idnum;
      var inportId = document.getElementById(idstr);
      outport = inportId.options[inportId.selectedIndex].value;
      toports[i-1] = outport;
    
      var idstr = "vol" + idnum;
      var volId = document.getElementById(idstr);
      volume = volId.value
      volumes[i-1] = volume

      var idstr = "rate" + idnum;
      var rateId = document.getElementById(idstr);
      flowRate = rateId.value
      flowrates[i-1] = flowRate;

      var idstr = "hours" + idnum;
      var hoursId = document.getElementById(idstr);
      hour = hoursId.value
      hours[i-1] = hour;

      var idstr = "minutes" + idnum;
      var minId = document.getElementById(idstr);
      minute = minId.value
      minutes[i-1] = minute;

      var idstr = "seconds" + idnum;
      var secId = document.getElementById(idstr);
      second = secId.value
      seconds[i-1] = second;

      var idstr = "cycles" + idnum;
      var cyclesId = document.getElementById(idstr);
      cycle = cyclesId.value
      cycles[i-1] = cycle;

      var idstr = "repeats" + idnum;
      var repeatsId = document.getElementById(idstr);
      repeat = repeatsId.value
      repeats[i-1] = repeat;
      
      

  }

    $.get('advProtocol',
              {'numitems': rowLength - 1,
               'fromports': JSON.stringify(fromports),
               'toports': JSON.stringify(toports),
               'serial_port': serport,
               'flowrates': JSON.stringify(flowrates),
               'volumes': JSON.stringify(volumes),
               'hours': JSON.stringify(hours),
               'minutes': JSON.stringify(minutes),
               'seconds': JSON.stringify(seconds),
               'cycles': JSON.stringify(cycles),
               'repeats': JSON.stringify(repeats)
                }
            );
    

    event.preventDefault();
});
$( "#saveProtocol" ).click(function( event ) {
  var serport = $( "#serial_port").val() || '';
  var oTable = document.getElementById('protocolTable');
  var rowLength = oTable.rows.length;
  var fromports = [];
  var toports = [];
  var hours = [];
  var minutes = [];
  var seconds = [];
  var flowrates = [];
  var volumes = [];
  var cycles = [];
  var repeats = [];


  for (i = 1; i < rowLength; i++){
      var oCells = oTable.rows.item(i).cells;

       //gets amount of cells of current row
      var cellLength = oCells.length;

      str = oCells.item(3).innerHTML;

      var numberPattern = /\d+/g;
      var idnum = str.match( numberPattern )[1]

      var idstr = "from" + idnum;
      var inportId = document.getElementById(idstr);
      inport = inportId.options[inportId.selectedIndex].value;
      fromports[i-1] = inport;

      var idstr = "to" + idnum;
      var inportId = document.getElementById(idstr);
      outport = inportId.options[inportId.selectedIndex].value;
      toports[i-1] = outport;
    
      var idstr = "vol" + idnum;
      var volId = document.getElementById(idstr);
      volume = volId.value
      volumes[i-1] = volume

      var idstr = "rate" + idnum;
      var rateId = document.getElementById(idstr);
      flowRate = rateId.value
      flowrates[i-1] = flowRate;

      var idstr = "hours" + idnum;
      var hoursId = document.getElementById(idstr);
      hour = hoursId.value
      hours[i-1] = hour;

      var idstr = "minutes" + idnum;
      var minId = document.getElementById(idstr);
      minute = minId.value
      minutes[i-1] = minute;

      var idstr = "seconds" + idnum;
      var secId = document.getElementById(idstr);
      second = secId.value
      seconds[i-1] = second;

      var idstr = "cycles" + idnum;
      var cyclesId = document.getElementById(idstr);
      cycle = cyclesId.value
      cycles[i-1] = cycle;

      var idstr = "repeats" + idnum;
      var repeatsId = document.getElementById(idstr);
      repeat = repeatsId.value
      repeats[i-1] = repeat;
      
      

  }

    $.get('saveProtocol',
              {'numitems': rowLength - 1,
               'fromports': JSON.stringify(fromports),
               'toports': JSON.stringify(toports),
               'serial_port': serport,
               'flowrates': JSON.stringify(flowrates),
               'volumes': JSON.stringify(volumes),
               'hours': JSON.stringify(hours),
               'minutes': JSON.stringify(minutes),
               'seconds': JSON.stringify(seconds),
               'cycles': JSON.stringify(cycles),
               'repeats': JSON.stringify(repeats)
                }
            );

    event.preventDefault();
});

last_changed = "vol"
second_to_last_changed = "rate"

$( "#newrows" ).click(function( event ) {
    var oTable = document.getElementById('protocolTable');
    var rowLength = oTable.rows.length;
    protocolItems = rowLength;
    //$("#addspot").append("hi").show();
    var table = document.getElementById("protocolTable");
    var row = table.insertRow(protocolItems);
    var cell1 = row.insertCell(0);
    var cell2 = row.insertCell(1);
    var cell3 = row.insertCell(2);
    var cell4 = row.insertCell(3);
    var cell5 = row.insertCell(4);
    var cell6 = row.insertCell(5);
    var cell7 = row.insertCell(6);
    var cell8 = row.insertCell(7);
    var cell9 = row.insertCell(8);
    var cell10 = row.insertCell(9);

    cell1.innerHTML = "<label>" + protocolItems + "</label>";
    cell2.innerHTML = "<div class = 'col-lg-16'><select id = 'from" + protocolItems + "' class='form-control'><option value='1'>1</option><option value='2'>2</option><option value='3'>3</option><option value='4'>4</option><option value='5'>5</option><option value='6'>6</option><option value='7'>7</option><option value='8'>8</option><option value='9'>9</option></select></div>";
    cell3.innerHTML = "<div class = 'col-lg-16'><select id = 'to" + protocolItems + "' class='form-control'><option value='1'>1</option><option value='2'>2</option><option value='3'>3</option><option value='4'>4</option><option value='5'>5</option><option value='6'>6</option><option value='7'>7</option><option value='8'>8</option><option value='9' selected>9</option></select></div>";
    cell4.innerHTML = "<div class = 'col-lg-16'><div class='form-group'><input id = 'hours" + protocolItems + "' class='form-control' value = '0'></div></div>";
    cell5.innerHTML = "<div class = 'col-lg-16'><div class='form-group'><input id = 'minutes" + protocolItems + "' class='form-control' value='0'></div></div>";
    cell6.innerHTML = "<div class = 'col-lg-16'><div class='form-group'><input id = 'seconds" + protocolItems + "' class='form-control' value='0'></div></div>"
    cell7.innerHTML = "<div class = 'col-lg-16'><div class='form-group'><div class='sandbox'><select id = 'rate" + protocolItems + "' class='demo-default' placeholder='ul/sec'><option value='0'>0</option><option value='8.333333333'>8.333333333</option><option value='10'>10</option><option value='11.66670556'>11.66670556</option><option value='13.33333333'>13.33333333</option><option value='15.00015'>15.00015</option><option value='16.66666667'>16.66666667</option><option value='25'>25</option><option value='33.33333333'>33.33333333</option><option value='41.66666667'>41.66666667</option><option value='50'>50</option><option value='66.66666667'>66.66666667</option><option value='74.99625019'>74.99625019</option><option value='83.33333333'>83.33333333</option><option value='91.65902841'>91.65902841</option><option value='100'>100</option><option value='108.3423619'>108.3423619</option><option value='116.6588894'>116.6588894</option><option value='125'>125</option><option value='133.3333333'>133.3333333</option><option value='141.6831964'>141.6831964</option><option value='150.0150015'>150.0150015</option><option value='158.3280557'>158.3280557</option><option value='166.6666667'>166.6666667</option><option value='333.3333333'>333.3333333</option><option value='666.6666667'>666.6666667</option><option value='833.3333333'>833.3333333</option><option value='1000'>1000</option><option value='1162.790698'>1162.790698</option><option value='1326.259947'>1326.259947</option><option value='1488.095238'>1488.095238</option><option value='1650.165017'>1650.165017</option><option value='1805.054152'>1805.054152</option><option value='2109.704641'>2109.704641</option><option value='2538.071066'>2538.071066</option><option value='2923.976608'>2923.976608</option><option value='3289.473684'>3289.473684</option><option value='3597.122302'>3597.122302</option><option value='3846.153846'>3846.153846</option></select></div></div></div>";
    cell8.innerHTML = "<div class = 'col-lg-16'><div class='form-group'><input id = 'vol" + protocolItems + "' class='form-control' value ='0' placeholder='ul'></div></div>"
    cell9.innerHTML = "<div class = 'col-lg-16'><select id = 'cycles" + protocolItems +"' class='form-control'><option value='na' selected>---</option><option value='Start'>Start</option><option value='End'>End</option></select> </div>";
    cell10.innerHTML = "<div class = 'col-lg-16'><div class='form-group'><input id = 'repeats" + protocolItems + "' class='form-control' placeholder='e.g. 5' value='0'></div></div>"
         
    tosel = '#rate' + protocolItems;                                    
                                       
    $(tosel).selectize();
    dynamicChanges(protocolItems)


    event.preventDefault();
});


function dynamicChanges(id_num){

  var hours_id = "#hours" + id_num
  var mins_id = "#minutes" + id_num
  var secs_id = "#seconds" + id_num
  var rate_id = "#rate" + id_num
  var vol_id = "#vol" + id_num

  $(hours_id).keyup(function(){
    hours_selected = $(hours_id).val()
    mins_selected = $(mins_id).val()
    secs_selected = $(secs_id).val()
    rate_selected = $(rate_id).val()
    vol_selected = $(vol_id).val()

    hours_val = parseInt(hours_selected)
    if(hours_selected == "")
      hours_val = 0
    mins_val = parseInt(mins_selected)
    if(mins_selected == "")
      mins_val = 0
    secs_val = parseInt(secs_selected)
    if(secs_selected == "")
      secs_val = 0

    time = hours_val*3600 + mins_val*60 + secs_val

    vol = parseInt(vol_selected)
    if(vol_selected == "")
      vol = 0
    rate = parseInt(rate_selected)
    if(rate_selected == "")
      rate = 0
    
    


    if(last_changed != "rate" && second_to_last_changed != "rate" && time != 0){
      rate = parseFloat(vol)/parseFloat(time)
      $(rate_id).val(rate)
    }
    else{
      vol = parseFloat(rate)*parseFloat(time)
      $(vol_id).val(vol)
    }

    if(last_changed != "time"){
      hold = last_changed
      last_changed = "time"
      second_to_last_changed = hold
    }
    
  });
  $(mins_id).keyup(function(){
    hours_selected = $(hours_id).val()
    mins_selected = $(mins_id).val()
    secs_selected = $(secs_id).val()
    rate_selected = $(rate_id).val()
    vol_selected = $(vol_id).val()
    hours_val = parseInt(hours_selected)
    if(hours_selected == "")
      hours_val = 0
    mins_val = parseInt(mins_selected)
    if(mins_selected == "")
      mins_val = 0
    secs_val = parseInt(secs_selected)
    if(secs_selected == "")
      secs_val = 0

    time = hours_val*3600 + mins_val*60 + secs_val
    
    vol = parseInt(vol_selected)
    if(vol_selected == "")
      vol = 0
    rate = parseInt(rate_selected)
    if(rate_selected == "")
      rate = 0
    
    if(last_changed != "rate" && second_to_last_changed != "rate" && time != 0){
      rate = parseFloat(vol)/parseFloat(time)
      $(rate_id).val(rate)
    }
    else{
      vol = parseFloat(rate)*parseFloat(time)
      $(vol_id).val(vol)
    }

    if(last_changed != "time"){
      hold = last_changed
      last_changed = "time"
      second_to_last_changed = hold
    }
  });
  $(secs_id).keyup(function(){
    hours_selected = $(hours_id).val()
    mins_selected = $(mins_id).val()
    secs_selected = $(secs_id).val()
    rate_selected = $(rate_id).val()
    vol_selected = $(vol_id).val()
    hours_val = parseInt(hours_selected)
    if(hours_selected == "")
      hours_val = 0
    mins_val = parseInt(mins_selected)
    if(mins_selected == "")
      mins_val = 0
    secs_val = parseInt(secs_selected)
    if(secs_selected == "")
      secs_val = 0

    time = hours_val*3600 + mins_val*60 + secs_val
    
    vol = parseInt(vol_selected)
    if(vol_selected == "")
      vol = 0
    rate = parseInt(rate_selected)
    if(rate_selected == "")
      rate = 0
    
    if(last_changed != "rate" && second_to_last_changed != "rate" && time != 0){
      rate = parseFloat(vol)/parseFloat(time)
      $(rate_id).val(rate)
    }
    else{
      vol = parseFloat(rate)*parseFloat(time)
      $(vol_id).val(vol)
    }

    if(last_changed != "time"){
      hold = last_changed
      last_changed = "time"
      second_to_last_changed = hold
    }

  });
  $(rate_id).keyup(function(){
    hours_selected = $(hours_id).val()
    mins_selected = $(mins_id).val()
    secs_selected = $(secs_id).val()
    rate_selected = $(rate_id).val()
    vol_selected = $(vol_id).val()
    hours_val = parseInt(hours_selected)
    if(hours_selected == "")
      hours_val = 0
    mins_val = parseInt(mins_selected)
    if(mins_selected == "")
      mins_val = 0
    secs_val = parseInt(secs_selected)
    if(secs_selected == "")
      secs_val = 0

    time = hours_val*3600 + mins_val*60 + secs_val
    
    vol = parseInt(vol_selected)
    if(vol_selected == "")
      vol = 0
    rate = parseInt(rate_selected)
    if(rate_selected == "")
      rate = 0

    if(last_changed != "time" && second_to_last_changed != "time" && vol != 0){
      time = parseFloat(vol)/parseFloat(rate)
      
      hours_amt = parseInt(parseInt(time)/3600)
      minutes_amt = parseInt((parseInt(time) % 3600)/60)
      secs_amt = parseInt(time) % 60

      $(hours_id).val(hours_amt)
      $(mins_id).val(minutes_amt)
      $(secs_id).val(secs_amt)
    }
    else{
      vol = parseFloat(rate)*parseFloat(time)
      $(vol_id).val(vol)
    }


    if(last_changed != "rate"){
      hold = last_changed
      last_changed = "rate"
      second_to_last_changed = hold
    }
    
  });
  $(vol_id).keyup(function(){
    hours_selected = $(hours_id).val()
    mins_selected = $(mins_id).val()
    secs_selected = $(secs_id).val()
    rate_selected = $(rate_id).val()
    vol_selected = $(vol_id).val()
    hours_val = parseInt(hours_selected)
    if(hours_selected == "")
      hours_val = 0
    mins_val = parseInt(mins_selected)
    if(mins_selected == "")
      mins_val = 0
    secs_val = parseInt(secs_selected)
    if(secs_selected == "")
      secs_val = 0

    time = hours_val*3600 + mins_val*60 + secs_val
    
    vol = parseInt(vol_selected)
    if(vol_selected == "")
      vol = 0
    rate = parseInt(rate_selected)
    if(rate_selected == "")
      rate = 0
    if(last_changed != "time" && second_to_last_changed != "time" && vol != 0){
      time = parseFloat(vol)/parseFloat(rate)
      
      hours_amt = parseInt(parseInt(time)/3600)
      minutes_amt = parseInt((parseInt(time) % 3600)/60)
      secs_amt = parseInt(time) % 60

      $(hours_id).val(hours_amt)
      $(mins_id).val(minutes_amt)
      $(secs_id).val(secs_amt)
    }
    else if(time != 0){
      rate = parseFloat(vol)/parseFloat(time)
      $(rate_id).val(rate)
    }

    if(last_changed != "vol"){
      hold = last_changed
      last_changed = "vol"
      second_to_last_changed = hold
    }
    
  });

}
dynamicChanges(1)


});
